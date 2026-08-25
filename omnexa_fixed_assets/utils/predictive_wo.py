# Copyright (c) 2026, Omnexa and contributors
# MIT License

"""Predictive / health-triggered work order factory."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import strip_html


def has_open_predictive_work_order(asset: str) -> bool:
	for doctype, filters in (
		(
			"Asset Work Order",
			{"asset": asset, "work_order_type": "Predictive", "status": ["not in", ["Completed", "Cancelled"]], "docstatus": ["<", 2]},
		),
		(
			"Core Work Order",
			{
				"subject_doctype": "Fixed Asset",
				"subject_name": asset,
				"work_order_type": "Predictive",
				"status": ["not in", ["Completed", "Cancelled"]],
				"docstatus": ["<", 2],
			},
		),
	):
		if frappe.db.exists("DocType", doctype) and frappe.db.exists(doctype, filters):
			return True
	return False


def create_predictive_work_order(
	asset_name: str,
	description: str,
	*,
	priority: str = "High",
	source: str = "predictive",
	auto_submit_asset_wo: bool = False,
) -> dict:
	if not asset_name or not frappe.db.exists("Fixed Asset", asset_name):
		frappe.throw(_("Asset {0} does not exist.").format(frappe.bold(asset_name or "?")))

	if has_open_predictive_work_order(asset_name):
		return {"ok": False, "skipped": True, "reason": "open_predictive_wo_exists"}

	asset = frappe.get_doc("Fixed Asset", asset_name)
	body = strip_html(description or "").strip() or _("Predictive maintenance for {0}").format(asset_name)

	aw = frappe.get_doc(
		{
			"doctype": "Asset Work Order",
			"company": asset.company,
			"branch": asset.branch,
			"asset": asset.name,
			"work_order_type": "Predictive",
			"priority": priority,
			"status": "Planned",
			"description": f"[{source}] {body}"[:4000],
		}
	)
	aw.insert(ignore_permissions=True)
	if auto_submit_asset_wo:
		aw.submit()

	core_wo = None
	if frappe.db.exists("DocType", "Core Work Order"):
		from erpgenex_maintenance_core.utils.work_management import ensure_core_work_order_for_asset_wo

		result = ensure_core_work_order_for_asset_wo(aw.name, auto_create=True)
		core_wo = result.get("core_work_order")

	return {"ok": True, "asset_work_order": aw.name, "core_work_order": core_wo, "source": source}
