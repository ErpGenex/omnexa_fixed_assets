# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from omnexa_fixed_assets.utils.feature_flags import (
	HOTEL_ASSETS_ACTIVITY_OPTION,
	site_has_any_hotel_assets_company,
)

SUPPORTED_FRAPPE_MAJOR = 15


def _remove_legacy_asset_insurance_workspace_slug():
	"""Drop stray ``asset-insurance`` Workspace row (same /app slug as **Asset Insurance**)."""
	if frappe.db.exists("Workspace", "asset-insurance") and frappe.db.exists("Workspace", "Asset Insurance"):
		try:
			frappe.delete_doc("Workspace", "asset-insurance", force=True, ignore_permissions=True)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Omnexa: remove duplicate asset-insurance Workspace")


def enforce_supported_frappe_version():
	"""Fail early when running on an unsupported Frappe major release."""
	version_text = (getattr(frappe, "__version__", "") or "").strip()
	if not version_text:
		return

	major_token = version_text.split(".", 1)[0]
	try:
		major = int(major_token)
	except ValueError:
		return

	if major != SUPPORTED_FRAPPE_MAJOR:
		frappe.throw(
			f"Unsupported Frappe version '{version_text}' for omnexa_fixed_assets. "
			"Supported range is >=15.0,<16.0.",
			frappe.ValidationError,
		)


def after_migrate():
	"""Additive enterprise EAM extensions; safe on existing sites."""
	ensure_enterprise_eam_custom_fields()
	refresh_hotel_vertical_from_company_activity()
	from omnexa_fixed_assets.workspace_analytics import ensure_fixed_assets_workspace_analytics

	ensure_fixed_assets_workspace_analytics()
	_remove_legacy_asset_insurance_workspace_slug()
	try:
		from omnexa_fixed_assets.asset_insurance_workspace import bootstrap_asset_insurance_desk

		bootstrap_asset_insurance_desk()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa: bootstrap_asset_insurance_desk")


def ensure_enterprise_eam_custom_fields():
	"""Add Maximo-inspired non-destructive fields to Fixed Asset."""
	if not frappe.db.exists("DocType", "Fixed Asset"):
		return
	custom_fields = {
		"Fixed Asset": [
			{
				"fieldname": "eam_hierarchy_section",
				"label": "Enterprise Hierarchy",
				"fieldtype": "Section Break",
				"insert_after": "tab_break_enterprise"
	},
			{"fieldname": "parent_asset", "label": "Parent Asset", "fieldtype": "Link", "options": "Fixed Asset", "insert_after": "eam_hierarchy_section"
	},
			{"fieldname": "asset_path", "label": "Asset Path", "fieldtype": "Data", "read_only": 1, "insert_after": "parent_asset"
	},
			{"fieldname": "asset_level", "label": "Asset Level", "fieldtype": "Int", "read_only": 1, "insert_after": "asset_path"
	},
			{"fieldname": "column_break_eam_h1", "fieldtype": "Column Break", "insert_after": "asset_level"
	},
			{"fieldname": "functional_location", "label": "Functional Location", "fieldtype": "Link", "options": "Functional Location", "insert_after": "column_break_eam_h1"
	},
			{"fieldname": "system_group", "label": "System Group", "fieldtype": "Data", "insert_after": "functional_location"
	},
			{"fieldname": "network_path", "label": "Network Path", "fieldtype": "Data", "insert_after": "system_group"
	},
			{
				"fieldname": "tab_break_eam_health",
				"label": "Health",
				"fieldtype": "Tab Break",
				"insert_after": "network_path"
	},
			{"fieldname": "eam_reliability_section", "label": "Reliability & Health", "fieldtype": "Section Break", "insert_after": "tab_break_eam_health"
	},
			{"fieldname": "mtbf", "label": "MTBF (hours)", "fieldtype": "Float", "read_only": 1, "insert_after": "eam_reliability_section"
	},
			{"fieldname": "mttr", "label": "MTTR (hours)", "fieldtype": "Float", "read_only": 1, "insert_after": "mtbf"
	},
			{"fieldname": "availability", "label": "Availability %", "fieldtype": "Percent", "read_only": 1, "insert_after": "mttr"
	},
			{"fieldname": "downtime", "label": "Downtime (hours)", "fieldtype": "Float", "read_only": 1, "insert_after": "availability"
	},
			{"fieldname": "uptime", "label": "Uptime (hours)", "fieldtype": "Float", "read_only": 1, "insert_after": "downtime"
	},
			{"fieldname": "failure_frequency", "label": "Failure Frequency", "fieldtype": "Float", "read_only": 1, "insert_after": "uptime"
	},
			{"fieldname": "reliability_score", "label": "Reliability Score", "fieldtype": "Percent", "read_only": 1, "insert_after": "failure_frequency"
	},
			{"fieldname": "column_break_eam_r1", "fieldtype": "Column Break", "insert_after": "reliability_score"
	},
			{"fieldname": "health_score", "label": "Health Score", "fieldtype": "Percent", "read_only": 1, "insert_after": "column_break_eam_r1"
	},
			{"fieldname": "health_status", "label": "Health Status", "fieldtype": "Select", "options": "\nCritical\nPoor\nFair\nGood\nExcellent", "read_only": 1, "insert_after": "health_score"
	},
			{"fieldname": "condition_state", "label": "Condition State", "fieldtype": "Select", "options": "\nUnknown\nNormal\nWatch\nAlert\nCritical", "insert_after": "health_status"
	},
			{"fieldname": "degradation_index", "label": "Degradation Index", "fieldtype": "Percent", "read_only": 1, "insert_after": "condition_state"
	},
			{"fieldname": "risk_score", "label": "Risk Score", "fieldtype": "Percent", "read_only": 1, "insert_after": "degradation_index"
	},
			{"fieldname": "confidence_score", "label": "Confidence Score", "fieldtype": "Percent", "read_only": 1, "insert_after": "risk_score"
	},
			{
				"fieldname": "tab_break_eam_monitoring",
				"label": "Monitoring",
				"fieldtype": "Tab Break",
				"insert_after": "confidence_score"
	},
			{"fieldname": "eam_operations_section", "label": "Operational Monitoring", "fieldtype": "Section Break", "insert_after": "tab_break_eam_monitoring"
	},
			{"fieldname": "runtime_hours", "label": "Runtime Hours", "fieldtype": "Float", "insert_after": "eam_operations_section"
	},
			{"fieldname": "operating_cycles", "label": "Operating Cycles", "fieldtype": "Int", "insert_after": "runtime_hours"
	},
			{"fieldname": "sensor_state", "label": "Sensor State", "fieldtype": "Select", "options": "\nUnknown\nOnline\nDegraded\nOffline\nSilent", "insert_after": "operating_cycles"
	},
			{"fieldname": "monitoring_enabled", "label": "Monitoring Enabled", "fieldtype": "Check", "default": "0", "insert_after": "sensor_state"
	},
			{"fieldname": "inspection_due", "label": "Inspection Due", "fieldtype": "Date", "insert_after": "monitoring_enabled"
	},
			{
				"fieldname": "tab_break_eam_cost",
				"label": "Lifecycle",
				"fieldtype": "Tab Break",
				"insert_after": "inspection_due"
	},
			{"fieldname": "eam_cost_intelligence_section", "label": "Lifecycle Cost Intelligence", "fieldtype": "Section Break", "insert_after": "tab_break_eam_cost"
	},
			{"fieldname": "lifecycle_cost", "label": "Lifecycle Cost", "fieldtype": "Currency", "read_only": 1, "insert_after": "eam_cost_intelligence_section"
	},
			{"fieldname": "maintenance_burden", "label": "Maintenance Burden", "fieldtype": "Percent", "read_only": 1, "insert_after": "lifecycle_cost"
	},
			{"fieldname": "replacement_projection", "label": "Replacement Projection", "fieldtype": "Currency", "read_only": 1, "insert_after": "maintenance_burden"
	},
			{"fieldname": "repair_efficiency", "label": "Repair Efficiency", "fieldtype": "Percent", "read_only": 1, "insert_after": "replacement_projection"
	},
			{"fieldname": "capital_risk", "label": "Capital Risk", "fieldtype": "Percent", "read_only": 1, "insert_after": "repair_efficiency"
	},
			{
				"fieldname": "tab_break_eam_strategy",
				"label": "Strategy",
				"fieldtype": "Tab Break",
				"insert_after": "capital_risk"
	},
			{"fieldname": "eam_strategy_section", "label": "Strategy", "fieldtype": "Section Break", "insert_after": "tab_break_eam_strategy"
	},
			{"fieldname": "criticality", "label": "Criticality", "fieldtype": "Select", "options": "\nLow\nMedium\nHigh\nSafety Critical", "insert_after": "eam_strategy_section"
	},
			{"fieldname": "maintenance_strategy", "label": "Maintenance Strategy", "fieldtype": "Link", "options": "Maintenance Strategy", "insert_after": "criticality"
	},
			{"fieldname": "replacement_recommendation", "label": "Replacement Recommendation", "fieldtype": "Small Text", "insert_after": "maintenance_strategy"
	},
		]
	}
	create_custom_fields(custom_fields, update=True)


def ensure_hotel_asset_management_custom_fields():
	"""Create conditional hotel extension fields on Fixed Asset when feature is enabled."""
	if not site_has_any_hotel_assets_company():
		return
	if not frappe.db.exists("DocType", "Fixed Asset"):
		return

	has_functional_area = frappe.db.exists("DocType", "Hotel Functional Area")
	hotel_zone_insert_after = "hotel_functional_area" if has_functional_area else "hotel_room"

	custom_fields = {
		"Fixed Asset": [
			{
				"fieldname": "tab_break_hotel",
				"label": "Hotel",
				"fieldtype": "Tab Break",
				"insert_after": "replacement_recommendation"
	},
			{
				"fieldname": "hotel_asset_section",
				"label": "Hotel Asset Management",
				"fieldtype": "Section Break",
				"insert_after": "tab_break_hotel"
	},
			{
				"fieldname": "hotel_property",
				"label": "Hotel Property",
				"fieldtype": "Link",
				"options": "Hotel Property",
				"insert_after": "hotel_asset_section"
	},
			{
				"fieldname": "hotel_room",
				"label": "Hotel Room",
				"fieldtype": "Link",
				"options": "Hotel Room",
				"insert_after": "hotel_property"
	},
			{
				"fieldname": "hotel_zone",
				"label": "Hotel Zone",
				"fieldtype": "Data",
				"insert_after": hotel_zone_insert_after
	},
			{
				"fieldname": "column_break_hotel_1",
				"fieldtype": "Column Break",
				"insert_after": "hotel_zone"
	},
			{
				"fieldname": "scan_status",
				"label": "Scan Status",
				"fieldtype": "Select",
				"options": "\nNot Scanned\nSeen\nMissing\nMismatch",
				"default": "Not Scanned",
				# rfid_tag is a native Fixed Asset field (Identification tab); do not duplicate as Custom Field.
				"insert_after": "column_break_hotel_1"
	},
			{
				"fieldname": "housekeeping_status",
				"label": "Housekeeping Status",
				"fieldtype": "Select",
				"options": "\nReady\nDirty\nOut of Service",
				"insert_after": "scan_status"
	},
			{
				"fieldname": "engineering_status",
				"label": "Engineering Status",
				"fieldtype": "Select",
				"options": "\nNormal\nOpen Work Order\nCritical",
				"insert_after": "housekeeping_status"
	},
			{
				"fieldname": "inspection_frequency_days",
				"label": "Inspection Frequency (Days)",
				"fieldtype": "Int",
				"insert_after": "engineering_status"
	},
			{
				"fieldname": "hotel_asset_ops_section",
				"label": "Hotel Asset Operations",
				"fieldtype": "Section Break",
				"insert_after": "inspection_frequency_days"
	},
			{
				"fieldname": "maintenance_cost_to_date",
				"label": "Maintenance Cost to Date",
				"fieldtype": "Currency",
				"read_only": 1,
				"insert_after": "hotel_asset_ops_section",
				"description": "Auto-calculated from Fixed Asset Maintenance records."
	},
			{
				"fieldname": "maintenance_event_count",
				"label": "Maintenance Events",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "maintenance_cost_to_date"
	},
			{
				"fieldname": "column_break_hotel_ops_1",
				"fieldtype": "Column Break",
				"insert_after": "maintenance_event_count"
	},
			{
				"fieldname": "inventory_scan_count",
				"label": "Inventory Scan Count",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "column_break_hotel_ops_1",
				"description": "Auto-calculated from RFID scan logs."
	},
			{
				"fieldname": "last_inventory_scan_at",
				"label": "Last Inventory Scan",
				"fieldtype": "Datetime",
				"read_only": 1,
				"insert_after": "inventory_scan_count"
	},
			{
				"fieldname": "hotel_asset_media_section",
				"label": "Asset Media & Attachments",
				"fieldtype": "Section Break",
				"insert_after": "last_inventory_scan_at"
	},
			{
				"fieldname": "image_count",
				"label": "Image Count",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "hotel_asset_media_section",
				"description": "Auto-calculated from media rows where type is Image."
	},
			{
				"fieldname": "attachment_count",
				"label": "Total Attachments",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "image_count",
				"description": "Auto-calculated from all media rows."
	},
			{
				"fieldname": "column_break_hotel_media_1",
				"fieldtype": "Column Break",
				"insert_after": "attachment_count"
	},
			{
				"fieldname": "asset_media_attachments",
				"label": "Media Files (Images, Videos, Documents)",
				"fieldtype": "Table",
				"options": "Asset Media Attachment",
				"insert_after": "column_break_hotel_media_1"
	},
		]
	}

	# Only add Link field if the referenced DocType exists on this site.
	if has_functional_area:
		custom_fields["Fixed Asset"].insert(
			4,
			{
				"fieldname": "hotel_functional_area",
				"label": "Hotel Functional Area",
				"fieldtype": "Link",
				"options": "Hotel Functional Area",
				"insert_after": "hotel_room"
	},
		)
	create_custom_fields(custom_fields, update=True)


def ensure_hotel_workspace_links():
	"""Append hotel-only links to Fixed Assets workspace when feature is enabled."""
	if not site_has_any_hotel_assets_company():
		return
	if not frappe.db.exists("Workspace", "Fixed Assets"):
		return

	ws = frappe.get_doc("Workspace", "Fixed Assets")
	existing = {(row.get("link_type"), row.get("link_to")) for row in (ws.links or []) if row.get("type") == "Link"}
	existing_cards = {row.get("label") for row in (ws.links or []) if row.get("type") == "Card Break"}

	def add_card(label: str):
		if label in existing_cards:
			return
		existing_cards.add(label)
		ws.append(
			"links",
			{"type": "Card Break", "label": label, "hidden": 0, "onboard": 0, "link_count": 0
	},
		)

	def add_link(label: str, link_type: str, link_to: str, is_query_report: int = 0):
		key = (link_type, link_to)
		if key in existing:
			return
		existing.add(key)
		ws.append(
			"links",
			{
				"type": "Link",
				"label": label,
				"link_type": link_type,
				"link_to": link_to,
				"is_query_report": is_query_report,
				"hidden": 0,
				"onboard": 0,
				"link_count": 0
	},
		)

	add_card("Hotel Asset Management")
	add_card("Hotel Setup")
	add_link("Hotel Property", "DocType", "Hotel Property")
	add_link("Hotel Functional Area", "DocType", "Hotel Functional Area")
	add_link("Hotel Room", "DocType", "Hotel Room")
	add_card("Hotel Operations")
	add_link("RFID Scan Log", "DocType", "RFID Scan Log")
	add_link("Hotel Asset Inspection", "DocType", "Hotel Asset Inspection")
	add_link("Hotel Asset Transfer", "DocType", "Hotel Asset Transfer")
	add_card("Hotel Maintenance & Quality")
	add_link("Asset Work Order", "DocType", "Asset Work Order")
	add_link("Fixed Asset Maintenance", "DocType", "Fixed Asset Maintenance")
	add_link("Asset Failure Event", "DocType", "Asset Failure Event")
	add_link("Fixed Asset Inspection", "DocType", "Fixed Asset Inspection")
	add_link("Asset Alert", "DocType", "Asset Alert")
	add_card("Hotel Finance & Forecasting")
	add_link("Asset Valuation Report", "Report", "Asset Valuation Report", is_query_report=1)
	add_link("Replacement Forecast Report", "Report", "Replacement Forecast Report", is_query_report=1)
	add_link("Inspection Compliance Report", "Report", "Inspection Compliance Report", is_query_report=1)
	add_link("Fixed Asset NBV by Category", "Report", "Fixed Asset NBV by Category", is_query_report=1)
	add_link("Asset Health Report", "Report", "Asset Health Report", is_query_report=1)
	add_card("Hotel Reports")
	add_link("Assets by Room", "Report", "Assets by Room", is_query_report=1)
	add_link("Hotel Assets by Floor", "Report", "Hotel Assets by Floor", is_query_report=1)
	add_link("Hotel Operational Asset Status", "Report", "Hotel Operational Asset Status", is_query_report=1)
	add_link("Hotel Inspection Summary", "Report", "Hotel Inspection Summary", is_query_report=1)
	add_link("Missing Assets", "Report", "Missing Assets", is_query_report=1)
	add_link("Last Seen Assets", "Report", "Last Seen Assets", is_query_report=1)
	add_link("Unscanned Assets", "Report", "Unscanned Assets", is_query_report=1)
	add_link("Hotel Movement History", "Report", "Hotel Movement History", is_query_report=1)
	add_link("Hotel Asset Depreciation", "Report", "Hotel Asset Depreciation", is_query_report=1)
	add_link("Warranty Expiring", "Report", "Warranty Expiring Assets", is_query_report=1)
	ws.save(ignore_permissions=True)


def ensure_hotel_roles():
	"""Create hotel asset management roles (kept dormant unless feature is enabled)."""
	if not site_has_any_hotel_assets_company():
		return

	for role_name, desk in (
		("Hotel Asset Admin", 1),
		("Engineering Manager", 1),
		("Housekeeping Supervisor", 1),
		("Finance Asset Controller", 1),
		("RFID Operator", 1),
		("Auditor", 1),
	):
		if frappe.db.exists("Role", role_name):
			continue
		r = frappe.new_doc("Role")
		r.role_name = role_name
		r.desk_access = desk
		r.is_custom = 1
		r.insert(ignore_permissions=True)


def ensure_hotel_report_roles():
	"""Synchronize hotel report access roles after JSON import/migrate."""
	if not site_has_any_hotel_assets_company():
		return
	report_roles = {
		"Assets by Room": [
			"System Manager",
			"Hotel Asset Admin",
			"Engineering Manager",
			"Housekeeping Supervisor",
			"Finance Asset Controller",
			"Auditor",
		],
		"Missing Assets": [
			"System Manager",
			"Hotel Asset Admin",
			"Engineering Manager",
			"Housekeeping Supervisor",
			"Finance Asset Controller",
			"Auditor",
		],
		"Last Seen Assets": [
			"System Manager",
			"Hotel Asset Admin",
			"Engineering Manager",
			"Housekeeping Supervisor",
			"RFID Operator",
			"Auditor",
		],
		"Unscanned Assets": [
			"System Manager",
			"Hotel Asset Admin",
			"Engineering Manager",
			"Housekeeping Supervisor",
			"RFID Operator",
			"Finance Asset Controller",
			"Auditor",
		],
		"Hotel Movement History": [
			"System Manager",
			"Hotel Asset Admin",
			"Engineering Manager",
			"Housekeeping Supervisor",
			"Finance Asset Controller",
			"Auditor",
		],
		"Hotel Asset Depreciation": [
			"System Manager",
			"Hotel Asset Admin",
			"Finance Asset Controller",
			"Auditor",
		],
		"Warranty Expiring Assets": [
			"System Manager",
			"Hotel Asset Admin",
			"Engineering Manager",
			"Finance Asset Controller",
			"Auditor",
		],
		"Hotel Assets by Floor": [
			"System Manager",
			"Hotel Asset Admin",
			"Engineering Manager",
			"Housekeeping Supervisor",
			"Finance Asset Controller",
			"Auditor",
		],
		"Hotel Inspection Summary": [
			"System Manager",
			"Hotel Asset Admin",
			"Engineering Manager",
			"Housekeeping Supervisor",
			"Auditor",
		],
		"Hotel Operational Asset Status": [
			"System Manager",
			"Hotel Asset Admin",
			"Engineering Manager",
			"Housekeeping Supervisor",
			"Finance Asset Controller",
			"Auditor",
		]}
	for report_name, roles in report_roles.items():
		if not frappe.db.exists("Report", report_name):
			continue
		doc = frappe.get_doc("Report", report_name)
		doc.roles = []
		for role in roles:
			if frappe.db.exists("Role", role):
				doc.append("roles", {"role": role
	})
		doc.save(ignore_permissions=True)


def refresh_hotel_vertical_from_company_activity():
	"""Hotel DocType fields, roles, report visibility, and Fixed Assets workspace links."""
	if not site_has_any_hotel_assets_company():
		return
	ensure_hotel_asset_management_custom_fields()
	ensure_hotel_roles()
	ensure_hotel_report_roles()
	ensure_hotel_workspace_links()


def company_on_save_sync_hotel_vertical(doc, method=None):
	"""After Company activity includes Hotel Assets, expose hotel shortcuts on `/app/fixed-assets`."""
	tracked = ("business_activity", "industry_sector", "production_demo_activity")
	if method == "after_insert":
		if not any((doc.get(f) or "").strip() == HOTEL_ASSETS_ACTIVITY_OPTION for f in tracked):
			return
	elif method == "on_update":
		if not any(doc.has_value_changed(f) for f in tracked):
			return
	else:
		return
	refresh_hotel_vertical_from_company_activity()
