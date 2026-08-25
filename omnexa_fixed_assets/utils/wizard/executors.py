# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Wizard step validation and atomic execution against existing DocTypes."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime, today

from omnexa_fixed_assets.utils.wizard.catalog import get_steps, get_wizard_def


def _data(session) -> dict:
	raw = session.step_data or "{}"
	if isinstance(raw, dict):
		return raw
	try:
		return json.loads(raw)
	except Exception:
		return {}


def _merge_step(session, step_key: str, payload: dict) -> dict:
	data = _data(session)
	data[step_key] = {**(data.get(step_key) or {}), **(payload or {})}
	return data


def validate_step(session, step_key: str, payload: dict | None = None) -> dict:
	wdef = get_wizard_def(session.wizard_type)
	if not wdef:
		frappe.throw(_("Unknown wizard type."))
	steps = {s["key"]: s for s in get_steps(session.wizard_type)}
	if step_key not in steps and step_key != "review":
		frappe.throw(_("Invalid wizard step."))

	merged = _merge_step(session, step_key, payload or {})
	step_def = steps.get(step_key) or {}
	errors = []
	for field in step_def.get("required_fields") or []:
		val = (merged.get(step_key) or {}).get(field)
		if val in (None, "", []):
			errors.append(_("{0} is required.").format(field))

	if step_key == "select_asset" or (merged.get("select_asset") or {}).get("fixed_asset"):
		asset = (merged.get("select_asset") or merged.get(step_key) or {}).get("fixed_asset") or merged.get(
			step_key, {}
		).get("fixed_asset")
		if asset and not frappe.db.exists("Fixed Asset", asset):
			errors.append(_("Asset not found."))

	if errors:
		return {"ok": False, "errors": errors}
	return {"ok": True, "step_data": merged}


def execute_wizard(session) -> dict:
	"""Atomic finalize — routes to wizard-specific executor."""
	executors = {
		"add_asset": _execute_add_asset,
		"transfer": _execute_transfer,
		"maintenance_send": _execute_maintenance_send,
		"maintenance_return": _execute_maintenance_return,
		"disposal": _execute_disposal,
		"depreciation": _execute_depreciation,
		"revaluation": _execute_revaluation,
		"location_correction": _execute_location_correction,
		"rfid_assignment": _execute_rfid_assignment,
		"audit_reconciliation": _execute_audit_reconciliation,
	}
	fn = executors.get(session.wizard_type)
	if not fn:
		frappe.throw(_("Wizard executor not implemented."))
	data = _data(session)
	for step in get_steps(session.wizard_type):
		if step["key"] == "review":
			continue
		v = validate_step(session, step["key"], data.get(step["key"]))
		if not v.get("ok"):
			frappe.throw("\n".join(v.get("errors") or [_("Incomplete wizard data.")]))
	return fn(session, data)


def _execute_add_asset(session, data: dict) -> dict:
	from omnexa_core.omnexa_core.user_context import get_navbar_form_defaults

	defaults = get_navbar_form_defaults()
	cls = data.get("classification") or {}
	basic = data.get("basic_info") or {}
	loc = data.get("location") or {}
	fin = data.get("financial") or {}
	dep = data.get("depreciation") or {}
	track = data.get("tracking") or {}
	insp = data.get("inspection") or {}

	asset = frappe.get_doc(
		{
			"doctype": "Fixed Asset",
			"company": session.company or defaults.get("company"),
			"branch": session.branch or defaults.get("branch"),
			"category": cls.get("category"),
			"asset_name": basic.get("asset_name"),
			"status": "draft",
			"acquisition_cost": flt(fin.get("acquisition_cost") or fin.get("capitalized_cost")),
			"capitalization_date": fin.get("capitalization_date") or today(),
			"salvage_value": flt(fin.get("salvage_value")),
			"depreciation_method": dep.get("depreciation_method") or "Straight Line",
			"useful_life_months": dep.get("useful_life_months") or 60,
			"depreciation_start_date": dep.get("depreciation_start_date"),
			"asset_gl_account": fin.get("asset_gl_account"),
			"accumulated_depreciation_gl_account": fin.get("accumulated_depreciation_gl_account"),
			"depreciation_expense_gl_account": fin.get("depreciation_expense_gl_account"),
			"warranty_supplier": (data.get("warranty") or {}).get("warranty_supplier"),
			"warranty_start_date": (data.get("warranty") or {}).get("warranty_start_date"),
			"warranty_end_date": (data.get("warranty") or {}).get("warranty_end_date"),
			"rfid_tag": track.get("rfid_tag"),
			"barcode": track.get("barcode"),
			"qr_payload": track.get("qr_payload"),
			"asset_owner": (data.get("ownership") or {}).get("asset_owner"),
			"notes": basic.get("notes"),
		}
	)
	asset.insert(ignore_permissions=True)

	updates = {}
	if loc.get("hotel_property"):
		updates["hotel_property"] = loc["hotel_property"]
	if loc.get("hotel_room"):
		updates["hotel_room"] = loc["hotel_room"]
	if loc.get("hotel_zone"):
		updates["hotel_zone"] = loc["hotel_zone"]
	if loc.get("exact_position"):
		updates["exact_position"] = loc["exact_position"]
	if updates:
		asset.db_set(updates, update_modified=False)

	inspection_name = None
	if insp.get("condition_status"):
		from omnexa_fixed_assets.api import submit_inspection

		out = submit_inspection(
			asset=asset.name,
			condition_status=insp.get("condition_status") or "Good",
			notes=insp.get("notes") or _("Initial inspection via Add Asset Wizard"),
		)
		inspection_name = out.get("inspection")

	if track.get("rfid_tag"):
		try:
			from omnexa_fixed_assets.api import scan_asset

			scan_asset(asset=asset.name, rfid_tag=track["rfid_tag"], location_text=loc.get("hotel_room") or _("Registration"))
		except Exception:
			pass

	return {
		"result_doctype": "Fixed Asset",
		"result_name": asset.name,
		"inspection": inspection_name,
	}


def _execute_transfer(session, data: dict) -> dict:
	sel = data.get("select_asset") or {}
	dest = data.get("destination") or {}
	reason = data.get("reason") or {}
	doc = frappe.get_doc(
		{
			"doctype": "Hotel Asset Transfer",
			"company": session.company,
			"branch": session.branch,
			"posting_date": reason.get("posting_date") or today(),
			"fixed_asset": sel.get("fixed_asset"),
			"to_hotel_property": dest.get("to_hotel_property") or dest.get("hotel_property"),
			"to_hotel_room": dest.get("to_hotel_room") or dest.get("hotel_room"),
			"approval_status": "Approved",
			"notes": reason.get("transfer_reason") or reason.get("notes"),
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return {"result_doctype": "Hotel Asset Transfer", "result_name": doc.name}


def _execute_maintenance_send(session, data: dict) -> dict:
	sel = data.get("select_asset") or {}
	wo = data.get("work_order") or {}
	doc = frappe.get_doc(
		{
			"doctype": "Asset Work Order",
			"company": session.company,
			"branch": session.branch,
			"asset": sel.get("fixed_asset"),
			"work_order_type": wo.get("work_order_type") or "Corrective",
			"priority": wo.get("priority") or "Medium",
			"status": "Planned",
			"description": wo.get("description"),
			"assigned_to": wo.get("assigned_to"),
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.set_value("Fixed Asset", sel["fixed_asset"], "status", "under_maintenance", update_modified=False)
	return {"result_doctype": "Asset Work Order", "result_name": doc.name}


def _execute_maintenance_return(session, data: dict) -> dict:
	sel = data.get("select_asset") or {}
	close = data.get("work_order_close") or {}
	cond = data.get("condition") or {}
	wo_name = close.get("work_order")
	if wo_name and frappe.db.exists("Asset Work Order", wo_name):
		frappe.db.set_value("Asset Work Order", wo_name, {"status": "Completed", "completion_date": today()}, update_modified=False)
	frappe.db.set_value("Fixed Asset", sel["fixed_asset"], "status", "in_use", update_modified=False)
	if cond.get("condition_status"):
		from omnexa_fixed_assets.api import submit_inspection

		submit_inspection(
			asset=sel["fixed_asset"],
			condition_status=cond["condition_status"],
			notes=cond.get("notes") or _("Return from maintenance wizard"),
		)
	return {"result_doctype": "Fixed Asset", "result_name": sel["fixed_asset"], "work_order": wo_name}


def _execute_disposal(session, data: dict) -> dict:
	sel = data.get("select_asset") or {}
	det = data.get("disposal_details") or {}
	acct = data.get("accounts") or {}
	doc = frappe.get_doc(
		{
			"doctype": "Fixed Asset Disposal",
			"company": session.company,
			"branch": session.branch,
			"fixed_asset": sel.get("fixed_asset"),
			"disposal_date": det.get("disposal_date") or today(),
			"proceeds": flt(det.get("proceeds")),
			"cash_account": acct.get("cash_account"),
			"gain_or_loss_account": acct.get("gain_or_loss_account"),
			"remarks": det.get("remarks"),
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return {"result_doctype": "Fixed Asset Disposal", "result_name": doc.name}


def _execute_depreciation(session, data: dict) -> dict:
	from omnexa_fixed_assets.utils.ias16 import suggest_monthly_depreciation

	sel = data.get("select_asset") or {}
	post = data.get("posting") or {}
	pd = getdate(post.get("posting_date") or today())
	amount = suggest_monthly_depreciation(sel["fixed_asset"], posting_date=pd)
	doc = frappe.get_doc(
		{
			"doctype": "Fixed Asset Depreciation Entry",
			"company": session.company,
			"branch": session.branch,
			"fixed_asset": sel["fixed_asset"],
			"posting_date": pd,
			"depreciation_amount": amount,
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return {"result_doctype": "Fixed Asset Depreciation Entry", "result_name": doc.name}


def _execute_revaluation(session, data: dict) -> dict:
	sel = data.get("select_asset") or {}
	ass = data.get("assessment") or {}
	if ass.get("revalued_amount"):
		doc = frappe.get_doc(
			{
				"doctype": "Fixed Asset Revaluation",
				"company": session.company,
				"branch": session.branch,
				"fixed_asset": sel["fixed_asset"],
				"posting_date": ass.get("posting_date") or today(),
				"revalued_amount": flt(ass["revalued_amount"]),
				"remarks": ass.get("remarks"),
			}
		)
		doc.insert(ignore_permissions=True)
		doc.submit()
		return {"result_doctype": "Fixed Asset Revaluation", "result_name": doc.name}
	if ass.get("condition_status"):
		from omnexa_fixed_assets.api import submit_inspection

		out = submit_inspection(
			asset=sel["fixed_asset"],
			condition_status=ass["condition_status"],
			notes=ass.get("remarks") or _("Condition review wizard"),
		)
		return {"result_doctype": "Hotel Asset Inspection", "result_name": out.get("inspection")}
	frappe.throw(_("Provide revalued amount or condition assessment."))


def _execute_location_correction(session, data: dict) -> dict:
	sel = data.get("select_asset") or {}
	loc = data.get("correct_location") or {}
	asset = sel.get("fixed_asset")
	updates = {}
	for f in ("hotel_property", "hotel_room", "hotel_zone", "exact_position"):
		if loc.get(f):
			updates[f] = loc[f]
	if updates:
		frappe.db.set_value("Fixed Asset", asset, updates, update_modified=False)
	log = frappe.get_doc(
		{
			"doctype": "Fixed Asset Movement Log",
			"company": session.company,
			"branch": session.branch,
			"posting_date": today(),
			"fixed_asset": asset,
			"movement_type": "inspection",
			"remarks": loc.get("remarks") or _("Location correction wizard"),
		}
	)
	log.insert(ignore_permissions=True)
	return {"result_doctype": "Fixed Asset Movement Log", "result_name": log.name}


def _execute_rfid_assignment(session, data: dict) -> dict:
	sel = data.get("select_asset") or {}
	tag = data.get("tag") or {}
	asset = sel.get("fixed_asset")
	rfid = (tag.get("rfid_tag") or "").strip()
	if not rfid:
		frappe.throw(_("RFID tag is required."))
	frappe.db.set_value("Fixed Asset", asset, "rfid_tag", rfid, update_modified=False)
	from omnexa_fixed_assets.api import scan_asset

	out = scan_asset(asset=asset, rfid_tag=rfid, location_text=tag.get("location_text") or _("RFID assignment"))
	return {"result_doctype": "Fixed Asset", "result_name": asset, "scan_log": out.get("scan_log")}


def _execute_audit_reconciliation(session, data: dict) -> dict:
	scope = data.get("scope") or {}
	findings = data.get("findings") or {}
	prop = scope.get("hotel_property")
	filters = {"company": session.company, "branch": session.branch}
	if prop:
		filters["hotel_property"] = prop
	assets = frappe.get_all("Fixed Asset", filters=filters, pluck="name", limit=500)
	created = 0
	for asset in assets:
		status = findings.get("default_condition") or "Good"
		if findings.get("inspect_all"):
			from omnexa_fixed_assets.api import submit_inspection

			submit_inspection(asset=asset, condition_status=status, notes=_("Audit reconciliation wizard"))
			created += 1
	return {"result_doctype": "Asset Lifecycle Wizard Session", "result_name": session.name, "inspections_created": created}


def resolve_asset(identifier: str) -> dict | None:
	identifier = (identifier or "").strip()
	if not identifier:
		return None
	for field in ("name", "rfid_tag", "barcode", "internal_code", "asset_tag"):
		name = frappe.db.get_value("Fixed Asset", {field: identifier}, "name")
		if name:
			row = frappe.db.get_value(
				"Fixed Asset",
				name,
				[
					"name",
					"asset_name",
					"status",
					"company",
					"branch",
					"hotel_property",
					"hotel_room",
					"hotel_zone",
					"rfid_tag",
					"net_book_value",
					"scan_status",
					"condition_state",
				],
				as_dict=True,
			)
			return row
	return None
