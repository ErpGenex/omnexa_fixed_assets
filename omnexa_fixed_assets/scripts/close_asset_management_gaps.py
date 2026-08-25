# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Close demo/UAT gaps: inspections, depreciation, movement logs, lifecycle data."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, add_months, getdate, now_datetime, today

CONDITIONS = ("Excellent", "Good", "Fair", "Poor", "Critical")


def _resolve_company_branch(company: str | None, branch: str | None) -> tuple[str, str]:
	if not company:
		company = frappe.defaults.get_user_default("omnexa_view_company") or frappe.db.get_single_value(
			"Global Defaults", "default_company"
		)
	if not company:
		frappe.throw(_("Company is required."))
	if not branch:
		branch = (
			frappe.db.get_value("Branch", {"company": company, "is_head_office": 1}, "name")
			or frappe.db.get_value("Branch", {"company": company}, "name")
		)
	if not branch:
		frappe.throw(_("No branch found for company {0}.").format(company))
	return company, branch


def ensure_category_depreciation_defaults(
	company: str,
	*,
	method: str = "Straight Line",
	useful_life_months: int = 60,
) -> dict:
	"""Set IAS 16 defaults on leaf fixed-asset categories when empty."""
	updated = []
	for row in frappe.get_all(
		"Fixed Asset Category",
		filters={"company": company, "is_group": 0},
		pluck="name",
	):
		cat = frappe.get_doc("Fixed Asset Category", row)
		changed = False
		if not (cat.default_depreciation_method or "").strip():
			cat.default_depreciation_method = method
			changed = True
		if not int(cat.default_useful_life_months or 0):
			cat.default_useful_life_months = useful_life_months
			changed = True
		if changed:
			cat.save(ignore_permissions=True)
			updated.append(row)
	return {"updated_categories": updated, "count": len(updated)}


def backfill_asset_depreciation_settings(company: str, branch: str | None = None) -> dict:
	"""Sync depreciation method / useful life from category onto assets."""
	filters = {"company": company}
	if branch:
		filters["branch"] = branch
	names = frappe.get_all("Fixed Asset", filters=filters, pluck="name")
	updated = 0
	for name in names:
		doc = frappe.get_doc("Fixed Asset", name)
		before = (doc.depreciation_method, doc.useful_life_months)
		doc._sync_depreciation_defaults_from_category()
		if not doc.depreciation_start_date and doc.capitalization_date:
			doc.depreciation_start_date = doc.capitalization_date
		after = (doc.depreciation_method, doc.useful_life_months)
		if after != before or not doc.depreciation_start_date:
			doc.db_set(
				{
					"depreciation_method": doc.depreciation_method,
					"useful_life_months": doc.useful_life_months,
					"depreciation_start_date": doc.depreciation_start_date,
				},
				update_modified=False,
			)
			updated += 1
	return {"assets_checked": len(names), "assets_updated": updated}


def seed_hotel_inspections(
	company: str,
	branch: str | None = None,
	*,
	limit: int = 200,
) -> dict:
	"""Create Hotel Asset Inspection rows for assets missing inspections."""
	from omnexa_fixed_assets import api as fa_api

	filters = {"company": company}
	if branch:
		filters["branch"] = branch
	assets = frappe.get_all(
		"Fixed Asset",
		filters=filters,
		fields=["name", "hotel_property", "hotel_room"],
		limit=limit,
		order_by="name asc",
	)
	created = []
	skipped = 0
	for idx, asset in enumerate(assets):
		exists = frappe.db.exists(
			"Hotel Asset Inspection",
			{"fixed_asset": asset.name, "company": company},
		)
		if exists:
			skipped += 1
			continue
		condition = CONDITIONS[idx % len(CONDITIONS)]
		inspection_date = str(add_days(today(), -(idx % 90)))
		out = fa_api.submit_inspection(
			asset=asset.name,
			condition_status=condition,
			inspection_date=inspection_date,
			hotel_property=asset.hotel_property,
			hotel_room=asset.hotel_room,
			notes="Demo inspection — gap closure seed",
		)
		created.append(out.get("inspection"))
	return {"created": len(created), "skipped": skipped, "sample": created[:5]}


def repair_invalid_asset_condition_states(company: str) -> dict:
	"""Fix assets where inspection sync wrote hotel labels into condition_state."""
	mapping = {
		"Excellent": "Normal",
		"Good": "Normal",
		"Fair": "Watch",
		"Poor": "Alert",
	}
	fixed = 0
	for row in frappe.get_all(
		"Fixed Asset",
		filters={"company": company, "condition_state": ["in", list(mapping.keys())]},
		pluck="name",
	):
		state = frappe.db.get_value("Fixed Asset", row, "condition_state")
		frappe.db.set_value("Fixed Asset", row, "condition_state", mapping.get(state, "Normal"), update_modified=False)
		fixed += 1
	return {"fixed_assets": fixed}


def run_depreciation_for_company(
	company: str,
	branch: str | None = None,
	*,
	posting_date: str | None = None,
	limit: int = 500,
) -> dict:
	from omnexa_fixed_assets import api as fa_api

	pd = posting_date or str(today())
	return fa_api.run_monthly_depreciation_batch(
		company=company,
		branch=branch,
		posting_date=pd,
		submit_entries=1,
		limit=limit,
	)


def backfill_movement_logs(company: str, branch: str | None = None) -> dict:
	"""Create movement log rows from transfers, inspections, scans, depreciation."""
	created = 0

	def _insert_log(**kwargs):
		nonlocal created
		if frappe.db.exists(
			"Fixed Asset Movement Log",
			{
				"fixed_asset": kwargs.get("fixed_asset"),
				"reference_doctype": kwargs.get("reference_doctype"),
				"reference_name": kwargs.get("reference_name"),
			},
		):
			return
		doc = frappe.get_doc({"doctype": "Fixed Asset Movement Log", **kwargs})
		doc.insert(ignore_permissions=True)
		created += 1

	transfer_filters = {"company": company, "docstatus": 1}
	if branch:
		transfer_filters["branch"] = branch
	for row in frappe.get_all(
		"Hotel Asset Transfer",
		filters=transfer_filters,
		fields=["name", "company", "branch", "posting_date", "fixed_asset", "from_hotel_room", "to_hotel_room"],
		limit=500,
	):
		_insert_log(
			company=row.company,
			branch=row.branch,
			posting_date=row.posting_date or today(),
			fixed_asset=row.fixed_asset,
			movement_type="transfer",
			remarks=f"Transfer {row.from_hotel_room or '?'} → {row.to_hotel_room or '?'}",
			reference_doctype="Hotel Asset Transfer",
			reference_name=row.name,
		)

	insp_filters = {"company": company}
	if branch:
		insp_filters["branch"] = branch
	for row in frappe.get_all(
		"Hotel Asset Inspection",
		filters=insp_filters,
		fields=["name", "company", "branch", "inspection_date", "fixed_asset", "condition_status"],
		limit=500,
	):
		_insert_log(
			company=row.company,
			branch=row.branch,
			posting_date=row.inspection_date or today(),
			fixed_asset=row.fixed_asset,
			movement_type="inspection",
			remarks=f"Inspection — {row.condition_status}",
			reference_doctype="Hotel Asset Inspection",
			reference_name=row.name,
		)

	scan_filters = {"company": company}
	if branch:
		scan_filters["branch"] = branch
	for row in frappe.get_all(
		"RFID Scan Log",
		filters=scan_filters,
		fields=["name", "company", "branch", "scan_time", "fixed_asset", "location_text", "scan_result"],
		limit=500,
	):
		_insert_log(
			company=row.company,
			branch=row.branch,
			posting_date=getdate(row.scan_time) if row.scan_time else today(),
			fixed_asset=row.fixed_asset,
			movement_type="transfer",
			remarks=f"RFID {row.scan_result or 'Scan'} @ {row.location_text or ''}".strip(),
			reference_doctype="RFID Scan Log",
			reference_name=row.name,
		)

	dep_filters = {"company": company, "docstatus": 1}
	if branch:
		dep_filters["branch"] = branch
	for row in frappe.get_all(
		"Fixed Asset Depreciation Entry",
		filters=dep_filters,
		fields=["name", "company", "branch", "posting_date", "fixed_asset", "depreciation_amount"],
		limit=500,
	):
		_insert_log(
			company=row.company,
			branch=row.branch,
			posting_date=row.posting_date or today(),
			fixed_asset=row.fixed_asset,
			movement_type="maintenance",
			remarks=f"Depreciation {row.depreciation_amount}",
			reference_doctype="Fixed Asset Depreciation Entry",
			reference_name=row.name,
		)

	return {"movement_logs_created": created}


@frappe.whitelist()
def close_asset_management_gaps(
	company: str | None = None,
	branch: str | None = None,
	inspection_limit: int | str = 200,
	depreciation_limit: int | str = 500,
) -> dict:
	"""Close all known fixed-assets UAT gaps for a company/branch scope."""
	frappe.only_for(("System Manager", "Administrator", "Hotel Asset Admin"))
	company, branch = _resolve_company_branch(company, branch)
	inspection_limit = int(inspection_limit or 200)
	depreciation_limit = int(depreciation_limit or 500)

	results = {
		"company": company,
		"branch": branch,
		"category_defaults": ensure_category_depreciation_defaults(company),
		"asset_depreciation_backfill": backfill_asset_depreciation_settings(company, branch),
		"condition_state_repair": repair_invalid_asset_condition_states(company),
		"inspections": seed_hotel_inspections(company, branch, limit=inspection_limit),
	}

	try:
		results["depreciation"] = run_depreciation_for_company(
			company, branch, limit=depreciation_limit
		)
	except Exception as exc:
		results["depreciation"] = {"ok": False, "error": str(exc)}

	results["movement_logs"] = backfill_movement_logs(company, branch)

	from omnexa_fixed_assets.scripts.audit_full_asset_management_scenario import (
		run_full_asset_management_audit,
	)

	results["post_audit"] = run_full_asset_management_audit(company=company, branch=branch)
	frappe.db.commit()
	return results


def run(company: str | None = None, branch: str | None = None):
	frappe.set_user("Administrator")
	return close_asset_management_gaps(company=company, branch=branch)
