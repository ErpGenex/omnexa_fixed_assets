# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Auto-fill child documents from Fixed Asset / hotel link fields."""

from __future__ import annotations

import frappe

from omnexa_fixed_assets.utils.hotel_field_defaults import (
	sync_company_branch_from_hotel_property,
	sync_hotel_fields_from_fixed_asset,
)

ASSET_LINK_FIELDS = ("fixed_asset", "asset")

# DocTypes that link to Fixed Asset (or asset) and should inherit scope + hotel placement.
ASSET_LINK_DOCTYPES = (
	"Fixed Asset Acquisition",
	"Fixed Asset Depreciation Entry",
	"Fixed Asset Disposal",
	"Fixed Asset Transfer",
	"Fixed Asset Write-Off",
	"Fixed Asset Revaluation",
	"Fixed Asset Maintenance",
	"Fixed Asset Inspection",
	"Fixed Asset Movement Log",
	"Hotel Asset Transfer",
	"Hotel Asset Inspection",
	"Asset Work Order",
	"Asset Alert",
	"Asset Meter Reading",
	"Asset Failure Event",
	"Asset Inspection",
	"Asset Condition Snapshot",
	"Asset Reliability Trend",
	"Asset Recommendation",
	"Asset Risk Matrix",
	"Asset Relationship",
	"RFID Scan Log",
	"Insurance Policy",
	"Asset Lifecycle Wizard Session",
)

FIXED_ASSET_AUTOFILL_FIELDS = (
	"asset_name",
	"company",
	"branch",
	"category",
	"status",
	"asset_owner",
	"hotel_property",
	"hotel_room",
	"hotel_zone",
	"functional_location",
	"asset_gl_account",
	"accumulated_depreciation_gl_account",
	"depreciation_expense_gl_account",
	"depreciation_method",
	"useful_life_months",
)

CATEGORY_AUTOFILL_FIELDS = (
	"default_depreciation_method",
	"default_useful_life_months",
	"asset_gl_account",
	"accumulated_depreciation_gl_account",
	"depreciation_expense_gl_account",
)


def _asset_link_value(doc) -> str | None:
	for field in ASSET_LINK_FIELDS:
		value = doc.get(field)
		if value:
			return value
	return None


def _set_if_field(doc, fieldname: str, value, *, overwrite: bool = False) -> None:
	if value in (None, "") or not doc.meta.has_field(fieldname):
		return
	if overwrite or not doc.get(fieldname):
		doc.set(fieldname, value)


def sync_scope_from_fixed_asset(doc, *, overwrite: bool = False) -> None:
	asset_name = _asset_link_value(doc)
	if not asset_name or not frappe.db.exists("Fixed Asset", asset_name):
		return

	asset = frappe.db.get_value("Fixed Asset", asset_name, FIXED_ASSET_AUTOFILL_FIELDS, as_dict=True)
	if not asset:
		return

	_set_if_field(doc, "company", asset.company, overwrite=overwrite)
	_set_if_field(doc, "branch", asset.branch, overwrite=overwrite)
	_set_if_field(doc, "asset_owner", asset.asset_owner, overwrite=overwrite)
	_set_if_field(doc, "asset_display", asset.asset_name, overwrite=overwrite)

	for target, source in (
		("hotel_property", "hotel_property"),
		("hotel_room", "hotel_room"),
		("hotel_zone", "hotel_zone"),
		("from_hotel_property", "hotel_property"),
		("from_hotel_room", "hotel_room"),
		("functional_location", "functional_location"),
	):
		_set_if_field(doc, target, asset.get(source), overwrite=overwrite)


def sync_category_defaults_on_fixed_asset(doc) -> None:
	if doc.doctype != "Fixed Asset" or not doc.get("category"):
		return
	cat = frappe.db.get_value(
		"Fixed Asset Category",
		doc.category,
		CATEGORY_AUTOFILL_FIELDS,
		as_dict=True,
	)
	if not cat:
		return
	mapping = {
		"depreciation_method": cat.default_depreciation_method,
		"useful_life_months": cat.default_useful_life_months,
		"asset_gl_account": cat.asset_gl_account,
		"accumulated_depreciation_gl_account": cat.accumulated_depreciation_gl_account,
		"depreciation_expense_gl_account": cat.depreciation_expense_gl_account,
	}
	for field, value in mapping.items():
		_set_if_field(doc, field, value, overwrite=False)


def autofill_from_asset_link(doc, method=None) -> None:
	"""Hook: populate linked fields before validate."""
	if doc.doctype == "Fixed Asset":
		sync_category_defaults_on_fixed_asset(doc)
		return

	if doc.doctype not in ASSET_LINK_DOCTYPES:
		return

	sync_company_branch_from_hotel_property(doc)
	sync_scope_from_fixed_asset(doc, overwrite=bool(_asset_link_value(doc)))
	sync_hotel_fields_from_fixed_asset(
		doc,
		property_field="hotel_property",
		room_field="hotel_room",
		only_if_empty=False,
	)
	if doc.meta.has_field("from_hotel_property") or doc.meta.has_field("from_hotel_room"):
		sync_hotel_fields_from_fixed_asset(
			doc,
			property_field="from_hotel_property",
			room_field="from_hotel_room",
			only_if_empty=False,
		)


@frappe.whitelist()
def get_fixed_asset_autofill(asset: str) -> dict:
	if not asset:
		return {"ok": False}
	if not frappe.has_permission("Fixed Asset", "read"):
		frappe.throw(frappe.PermissionError)
	row = frappe.db.get_value("Fixed Asset", asset, FIXED_ASSET_AUTOFILL_FIELDS, as_dict=True)
	return {"ok": bool(row), "asset": row or {}}


@frappe.whitelist()
def get_category_autofill(category: str) -> dict:
	if not category:
		return {"ok": False}
	if not frappe.has_permission("Fixed Asset Category", "read"):
		frappe.throw(frappe.PermissionError)
	row = frappe.db.get_value("Fixed Asset Category", category, CATEGORY_AUTOFILL_FIELDS, as_dict=True)
	return {"ok": bool(row), "category": row or {}}


def patch_doc_events(doc_events: dict) -> None:
	"""Append autofill hook to asset-link DocTypes (called from hooks.py)."""
	handler = "omnexa_fixed_assets.utils.fa_doc_autofill.autofill_from_asset_link"
	for dt in ASSET_LINK_DOCTYPES:
		entry = doc_events.setdefault(dt, {})
		current = entry.get("before_validate")
		if not current:
			entry["before_validate"] = handler
		elif isinstance(current, str):
			if current != handler:
				entry["before_validate"] = [current, handler]
		elif isinstance(current, list):
			if handler not in current:
				current.append(handler)
	if "Fixed Asset" not in doc_events:
		doc_events["Fixed Asset"] = {}
	fa = doc_events["Fixed Asset"]
	current = fa.get("before_validate")
	if not current:
		fa["before_validate"] = handler
	elif isinstance(current, str) and current != handler:
		fa["before_validate"] = [current, handler]
	elif isinstance(current, list) and handler not in current:
		current.append(handler)
