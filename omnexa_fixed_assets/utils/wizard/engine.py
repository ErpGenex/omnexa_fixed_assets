# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Asset Lifecycle Wizard engine — draft, validate, submit."""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import now_datetime

from omnexa_fixed_assets.utils.wizard.catalog import get_steps, get_wizard_def
from omnexa_fixed_assets.utils.wizard.executors import execute_wizard, validate_step


def start_wizard(wizard_type: str, company: str, branch: str | None = None) -> dict:
	if not get_wizard_def(wizard_type):
		frappe.throw(_("Unknown wizard type: {0}").format(wizard_type))
	doc = frappe.get_doc(
		{
			"doctype": "Asset Lifecycle Wizard Session",
			"wizard_type": wizard_type,
			"status": "Draft",
			"current_step": 0,
			"company": company,
			"branch": branch,
			"step_data": "{}",
			"owner_user": frappe.session.user,
		}
	)
	doc.insert(ignore_permissions=True)
	return _session_payload(doc)


def get_session(name: str) -> dict:
	doc = frappe.get_doc("Asset Lifecycle Wizard Session", name)
	return _session_payload(doc)


def save_wizard_step(session_name: str, step_key: str, payload: dict | None = None) -> dict:
	doc = frappe.get_doc("Asset Lifecycle Wizard Session", session_name)
	if doc.status in ("Completed", "Cancelled"):
		frappe.throw(_("Cannot edit a {0} wizard session.").format(doc.status))
	result = validate_step(doc, step_key, payload or {})
	if not result.get("ok"):
		return {"ok": False, "errors": result.get("errors")}

	doc.step_data = json.dumps(result["step_data"], ensure_ascii=False)
	steps = get_steps(doc.wizard_type)
	for idx, step in enumerate(steps):
		if step["key"] == step_key:
			doc.current_step = idx
			break
	if doc.status == "Draft":
		doc.status = "In Progress"
	sel = (result.get("step_data") or {}).get("select_asset") or {}
	if sel.get("fixed_asset"):
		doc.fixed_asset = sel["fixed_asset"]
	doc.save(ignore_permissions=True)
	return {"ok": True, "session": _session_payload(doc)}


def submit_wizard(session_name: str) -> dict:
	doc = frappe.get_doc("Asset Lifecycle Wizard Session", session_name)
	if doc.status == "Completed":
		return {"ok": True, "session": _session_payload(doc), "message": _("Already completed.")}
	if doc.status == "Cancelled":
		frappe.throw(_("Wizard session was cancelled."))

	doc.status = "Processing"
	doc.save(ignore_permissions=True)
	try:
		result = execute_wizard(doc)
		doc.reload()
		doc.status = "Completed"
		doc.completed_at = now_datetime()
		doc.result_doctype = result.get("result_doctype")
		doc.result_name = result.get("result_name")
		doc.result_detail = json.dumps({k: v for k, v in result.items() if k not in ("result_doctype", "result_name")})
		doc.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception as exc:
		frappe.db.rollback()
		doc.reload()
		doc.status = "Failed"
		doc.error_message = str(exc)[:500]
		doc.save(ignore_permissions=True)
		frappe.log_error(frappe.get_traceback(), f"Wizard submit failed: {session_name}")
		raise

	return {"ok": True, "session": _session_payload(doc), "result": result}


def cancel_wizard(session_name: str) -> dict:
	doc = frappe.get_doc("Asset Lifecycle Wizard Session", session_name)
	if doc.status == "Completed":
		frappe.throw(_("Cannot cancel a completed wizard."))
	doc.status = "Cancelled"
	doc.save(ignore_permissions=True)
	return {"ok": True, "session": _session_payload(doc)}


def list_wizard_drafts(company: str | None = None, wizard_type: str | None = None, limit: int = 20) -> list[dict]:
	filters: dict = {"status": ["in", ["Draft", "In Progress", "Failed"]], "owner_user": frappe.session.user}
	if company:
		filters["company"] = company
	if wizard_type:
		filters["wizard_type"] = wizard_type
	return frappe.get_all(
		"Asset Lifecycle Wizard Session",
		filters=filters,
		fields=["name", "wizard_type", "status", "current_step", "modified", "company", "branch"],
		order_by="modified desc",
		limit=limit,
	)


def _session_payload(doc) -> dict:
	data = doc.step_data or "{}"
	if isinstance(data, str):
		try:
			data = json.loads(data)
		except Exception:
			data = {}
	steps = get_steps(doc.wizard_type)
	wdef = get_wizard_def(doc.wizard_type) or {}
	return {
		"name": doc.name,
		"wizard_type": doc.wizard_type,
		"title": wdef.get("title"),
		"status": doc.status,
		"current_step": doc.current_step or 0,
		"steps": steps,
		"step_data": data,
		"company": doc.company,
		"branch": doc.branch,
		"result_doctype": doc.result_doctype,
		"result_name": doc.result_name,
		"error_message": doc.error_message,
	}
