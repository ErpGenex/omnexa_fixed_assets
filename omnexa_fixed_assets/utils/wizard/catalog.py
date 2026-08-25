# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Asset Lifecycle Wizard catalog — step definitions for desk UI."""

from __future__ import annotations

WIZARD_TYPES = {
	"add_asset": {
		"title": "Add Asset Wizard",
		"title_ar": "معالج إضافة أصل",
		"description": "Register a new fixed asset with location, finance, RFID, and inspection.",
		"icon": "add",
		"steps": [
			{"key": "classification", "label": "Classification", "required_fields": ["category"]},
			{"key": "basic_info", "label": "Basic Info", "required_fields": ["asset_name"]},
			{"key": "location", "label": "Location", "required_fields": []},
			{"key": "financial", "label": "Financial", "required_fields": []},
			{"key": "depreciation", "label": "Depreciation", "required_fields": []},
			{"key": "tracking", "label": "RFID / Tracking", "required_fields": []},
			{"key": "inspection", "label": "Initial Inspection", "required_fields": []},
			{"key": "review", "label": "Review", "required_fields": []},
		],
	},
	"transfer": {
		"title": "Asset Transfer Wizard",
		"title_ar": "معالج نقل أصل",
		"description": "Move asset between hotel rooms/properties with full audit trail.",
		"icon": "move",
		"steps": [
			{"key": "select_asset", "label": "Select Asset", "required_fields": ["fixed_asset"]},
			{"key": "current_location", "label": "Current Location", "required_fields": []},
			{"key": "destination", "label": "Destination", "required_fields": ["to_hotel_room"]},
			{"key": "reason", "label": "Transfer Reason", "required_fields": ["transfer_reason"]},
			{"key": "review", "label": "Review", "required_fields": []},
		],
	},
	"maintenance_send": {
		"title": "Send to Maintenance Wizard",
		"title_ar": "معالج إرسال للصيانة",
		"description": "Create work order and mark asset under maintenance.",
		"icon": "tool",
		"steps": [
			{"key": "select_asset", "label": "Select Asset", "required_fields": ["fixed_asset"]},
			{"key": "work_order", "label": "Work Order", "required_fields": ["description"]},
			{"key": "authorization", "label": "Authorization", "required_fields": []},
			{"key": "review", "label": "Review", "required_fields": []},
		],
	},
	"maintenance_return": {
		"title": "Return from Maintenance Wizard",
		"title_ar": "معالج إرجاع من الصيانة",
		"description": "Close work order and restore asset to service.",
		"icon": "check",
		"steps": [
			{"key": "select_asset", "label": "Select Asset", "required_fields": ["fixed_asset"]},
			{"key": "work_order_close", "label": "Close Work Order", "required_fields": ["work_order"]},
			{"key": "condition", "label": "Condition Review", "required_fields": ["condition_status"]},
			{"key": "review", "label": "Review", "required_fields": []},
		],
	},
	"disposal": {
		"title": "Disposal / Scrapping Wizard",
		"title_ar": "معالج التخلص من الأصل",
		"description": "IAS 16 derecognition with GL posting.",
		"icon": "delete",
		"steps": [
			{"key": "select_asset", "label": "Select Asset", "required_fields": ["fixed_asset"]},
			{"key": "disposal_details", "label": "Disposal Details", "required_fields": ["disposal_date"]},
			{"key": "accounts", "label": "GL Accounts", "required_fields": ["cash_account", "gain_or_loss_account"]},
			{"key": "review", "label": "Review", "required_fields": []},
		],
	},
	"depreciation": {
		"title": "Depreciation Wizard",
		"title_ar": "معالج الإهلاك",
		"description": "Post depreciation entry for selected asset(s).",
		"icon": "percentage",
		"steps": [
			{"key": "select_asset", "label": "Select Asset", "required_fields": ["fixed_asset"]},
			{"key": "posting", "label": "Posting Date", "required_fields": ["posting_date"]},
			{"key": "preview", "label": "Preview", "required_fields": []},
			{"key": "review", "label": "Review", "required_fields": []},
		],
	},
	"revaluation": {
		"title": "Revaluation / Condition Review Wizard",
		"title_ar": "معالج إعادة التقييم",
		"description": "Update asset value or condition assessment.",
		"icon": "rating",
		"steps": [
			{"key": "select_asset", "label": "Select Asset", "required_fields": ["fixed_asset"]},
			{"key": "assessment", "label": "Assessment", "required_fields": []},
			{"key": "review", "label": "Review", "required_fields": []},
		],
	},
	"location_correction": {
		"title": "Location Correction Wizard",
		"title_ar": "معالج تصحيح الموقع",
		"description": "Correct hotel location without full transfer workflow.",
		"icon": "map-pin",
		"steps": [
			{"key": "select_asset", "label": "Select Asset", "required_fields": ["fixed_asset"]},
			{"key": "correct_location", "label": "Correct Location", "required_fields": ["hotel_property"]},
			{"key": "review", "label": "Review", "required_fields": []},
		],
	},
	"rfid_assignment": {
		"title": "RFID Assignment Wizard",
		"title_ar": "معالج ربط RFID",
		"description": "Assign or replace RFID tag on asset.",
		"icon": "scan",
		"steps": [
			{"key": "select_asset", "label": "Select Asset", "required_fields": ["fixed_asset"]},
			{"key": "tag", "label": "RFID Tag", "required_fields": ["rfid_tag"]},
			{"key": "review", "label": "Review", "required_fields": []},
		],
	},
	"audit_reconciliation": {
		"title": "Asset Audit / Reconciliation Wizard",
		"title_ar": "معالج تدقيق الأصول",
		"description": "Reconcile physical scan vs register; create inspections.",
		"icon": "search",
		"steps": [
			{"key": "scope", "label": "Audit Scope", "required_fields": ["hotel_property"]},
			{"key": "findings", "label": "Findings", "required_fields": []},
			{"key": "review", "label": "Review", "required_fields": []},
		],
	},
}


def get_catalog() -> list[dict]:
	return [
		{"wizard_type": k, **{kk: vv for kk, vv in v.items() if kk != "steps"}, "step_count": len(v["steps"])}
		for k, v in WIZARD_TYPES.items()
	]


def get_wizard_def(wizard_type: str) -> dict | None:
	return WIZARD_TYPES.get(wizard_type)


def get_steps(wizard_type: str) -> list[dict]:
	defn = WIZARD_TYPES.get(wizard_type) or {}
	return list(defn.get("steps") or [])
