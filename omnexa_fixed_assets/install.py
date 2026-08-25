# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from omnexa_fixed_assets.utils.feature_flags import (
	HOTEL_ASSETS_ACTIVITY_OPTION,
	site_has_any_hotel_assets_company,
)

# Desk Page roles — must include All + Company Admin so ERP users are not blocked.
HOSPITALITY_DESK_PAGE_ROLES = (
	"System Manager",
	"All",
	"Desk User",
	"Company Admin",
	"Accounts Manager",
	"Accounts User",
	"Hotel Asset Admin",
	"Hotel General Manager",
	"Hotel Branch Manager",
	"Engineering Manager",
	"Housekeeping Supervisor",
	"Hotel Housekeeping",
	"Hotel Front Desk",
	"Finance Asset Controller",
	"RFID Operator",
	"Auditor",
)

HOSPITALITY_DESK_PAGES = (
	"fa-hotel-assets-dashboard",
	"fa-live-asset-tracking",
	"fa-linen-dashboard",
	"fa-hospitality-command-center",
	"fa-global-hospitality-portfolio",
	"fa-asset-wizards",
	"fa-executive-dashboard",
	"fa-asset-scan-pwa",
)

FIXED_ASSETS_DESK_PAGES = (
	"fixed-assets-workcenter",
	"fixed-assets-executive-dashboard",
	"fixed-assets-analytics-dashboard",
	"fixed-assets-operations-desk",
	"fixed-assets-finance-desk",
	"fixed-assets-customer-portal",
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


def ensure_fixed_assets_workspace():
	"""Sync Fixed Assets workspace so /app/fixed-assets resolves on desk."""
	if getattr(frappe.flags, "in_test", False):
		return
	import os

	from frappe.modules.import_file import import_file_by_path

	json_path = os.path.join(
		frappe.get_app_path("omnexa_fixed_assets"),
		"omnexa_fixed_assets",
		"workspace",
		"fixed_assets",
		"fixed_assets.json",
	)
	if os.path.exists(json_path):
		import_file_by_path(json_path, force=True, ignore_version=True)

	target_name = "Fixed Assets"
	if not frappe.db.exists("Workspace", target_name) and frappe.db.exists("Workspace", "Fixed assets"):
		try:
			frappe.rename_doc("Workspace", "Fixed assets", target_name, force=True, ignore_permissions=True)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Omnexa: rename Fixed assets workspace")

	if frappe.db.exists("Workspace", target_name):
		frappe.db.set_value(
			"Workspace",
			target_name,
			{"public": 1, "is_hidden": 0, "title": "Fixed assets"},
			update_modified=False,
		)
	frappe.clear_cache(doctype="Workspace")


def after_migrate():
	"""Additive enterprise EAM extensions; safe on existing sites."""
	try:
		from omnexa_fixed_assets.utils.navbar_scope import ensure_fixed_assets_navbar_scope_fields

		ensure_fixed_assets_navbar_scope_fields()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa FA: navbar scope fields")
	ensure_enterprise_eam_custom_fields()
	ensure_fixed_assets_workspace()
	ensure_hotel_assets_dashboard_page()
	ensure_tracking_pages()
	ensure_rfid_offline_custom_fields()
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
				"fetch_from": "hotel_room.wing",
				"fetch_if_empty": 1,
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
				"fetch_from": "hotel_room.hotel_functional_area",
				"fetch_if_empty": 1,
				"insert_after": "hotel_room"
	},
		)
	create_custom_fields(custom_fields, update=True)


def ensure_rfid_offline_custom_fields():
	"""Offline sync metadata on RFID Scan Log (additive)."""
	create_custom_fields(
		{
			"RFID Scan Log": [
				{
					"fieldname": "external_event_id",
					"label": "External Event ID",
					"fieldtype": "Data",
					"insert_after": "notes",
					"read_only": 1,
					"unique": 1,
				},
				{
					"fieldname": "sequence_number",
					"label": "Sequence Number",
					"fieldtype": "Int",
					"insert_after": "external_event_id",
					"read_only": 1,
				},
			]
		},
		update=True,
	)


def _sync_page_roles(page_name: str, roles: tuple[str, ...]) -> None:
	if not frappe.db.exists("Page", page_name):
		return
	page = frappe.get_doc("Page", page_name)
	page.roles = []
	for role in roles:
		if frappe.db.exists("Role", role):
			page.append("roles", {"role": role})
	page.save(ignore_permissions=True)


def ensure_hospitality_desk_page_roles():
	"""Align hospitality desk pages with the same role set (prevents Not permitted)."""
	for page_name in HOSPITALITY_DESK_PAGES:
		try:
			_sync_page_roles(page_name, HOSPITALITY_DESK_PAGE_ROLES)
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Omnexa: page roles {page_name}")


def ensure_fixed_assets_desk_page_roles():
	roles = HOSPITALITY_DESK_PAGE_ROLES
	for page_name in FIXED_ASSETS_DESK_PAGES:
		try:
			_sync_page_roles(page_name, roles)
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Omnexa: FA desk page roles {page_name}")


def ensure_tracking_pages():
	"""Import live map and linen dashboard pages."""
	import os

	from frappe.modules.import_file import import_file_by_path

	base = os.path.join(frappe.get_app_path("omnexa_fixed_assets"), "omnexa_fixed_assets", "page")
	for page_dir in (
		"fa_live_asset_tracking",
		"fa_linen_dashboard",
		"fa_hospitality_command_center",
		"fa_global_hospitality_portfolio",
		"fa_asset_wizards",
	):
		json_path = os.path.join(base, page_dir, f"{page_dir}.json")
		if os.path.exists(json_path):
			import_file_by_path(json_path, force=True, ignore_version=True)
	ensure_hospitality_desk_page_roles()
	ensure_fixed_assets_desk_page_roles()


def ensure_hotel_assets_dashboard_page():
	"""Import/sync the hotel assets desk page (idempotent)."""
	import os

	from frappe.modules.import_file import import_file_by_path

	json_path = os.path.join(
		frappe.get_app_path("omnexa_fixed_assets"),
		"omnexa_fixed_assets",
		"page",
		"fa_hotel_assets_dashboard",
		"fa_hotel_assets_dashboard.json",
	)
	if os.path.exists(json_path):
		import_file_by_path(json_path, force=True, ignore_version=True)
	_sync_page_roles("fa-hotel-assets-dashboard", HOSPITALITY_DESK_PAGE_ROLES)


def ensure_fixed_assets_workspace_menus():
	"""Rebuild Fixed Assets sidebar + home content from the full workspace catalog."""
	from omnexa_fixed_assets.workspace.fa_workspace import sync_fa_workspace_menu

	try:
		sync_fa_workspace_menu(save=True, rebuild=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa: ensure_fixed_assets_workspace_menus")
	if site_has_any_hotel_assets_company():
		ensure_hotel_workspace_links()


def ensure_hotel_workspace_links():
	"""Append any hotel DocType/report links missing after workspace sync (no empty card breaks)."""
	if not site_has_any_hotel_assets_company():
		return
	if not frappe.db.exists("Workspace", "Fixed Assets"):
		return

	from omnexa_fixed_assets.workspace.fa_workspace import HOTEL_WORKSPACE_SECTIONS

	ws = frappe.get_doc("Workspace", "Fixed Assets")
	existing = {(row.get("link_type"), row.get("link_to")) for row in (ws.links or []) if row.get("type") == "Link"}
	changed = False

	def _target_exists(link_type: str, link_to: str) -> bool:
		if link_type == "DocType":
			return bool(frappe.db.exists("DocType", link_to))
		if link_type == "Report":
			return bool(frappe.db.exists("Report", link_to))
		if link_type == "Page":
			return bool(frappe.db.exists("Page", link_to))
		return False

	for card_label, items in HOTEL_WORKSPACE_SECTIONS:
		missing = []
		for link_type, link_to, label in items:
			if not _target_exists(link_type, link_to):
				continue
			if (link_type, link_to) in existing:
				continue
			missing.append((link_type, link_to, label))
		if not missing:
			continue
		ws.append(
			"links",
			{"type": "Card Break", "label": card_label, "hidden": 0, "onboard": 0, "link_count": 0},
		)
		for link_type, link_to, label in missing:
			ws.append(
				"links",
				{
					"type": "Link",
					"label": label,
					"link_type": link_type,
					"link_to": link_to,
					"is_query_report": 1 if link_type == "Report" else 0,
					"hidden": 0,
					"onboard": 0,
					"link_count": 0,
				},
			)
			existing.add((link_type, link_to))
			changed = True

	if changed:
		try:
			ws.save(ignore_permissions=True)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Omnexa: ensure_hotel_workspace_links")


HOTEL_DASHBOARD_SHORTCUT_LABEL = "Hotel Assets Dashboard"
HOTEL_DASHBOARD_PAGE = "fa-hotel-assets-dashboard"


def _ensure_hotel_dashboard_workspace_shortcut(ws) -> bool:
	"""Prominent dashboard tile on Fixed Assets workspace home (Dashboards section)."""
	import json

	changed = False
	shortcut_labels = {row.label for row in (ws.shortcuts or []) if row.label}
	if HOTEL_DASHBOARD_SHORTCUT_LABEL not in shortcut_labels:
		ws.append(
			"shortcuts",
			{
				"label": HOTEL_DASHBOARD_SHORTCUT_LABEL,
				"type": "Page",
				"link_to": HOTEL_DASHBOARD_PAGE,
				"icon": "hotel",
				"color": "Orange",
				"doc_view": "",
			},
		)
		changed = True

	# Sidebar link under 📊 Dashboards (with icon), not only at bottom of workspace.
	if ("Page", HOTEL_DASHBOARD_PAGE) not in {
		(row.link_type, row.link_to) for row in (ws.links or []) if row.type == "Link"
	}:
		insert_at = None
		for idx, row in enumerate(ws.links or []):
			if row.type == "Link" and row.link_to == "fa-asset-scan-pwa":
				insert_at = idx + 1
				break
		link_row = {
			"type": "Link",
			"label": HOTEL_DASHBOARD_SHORTCUT_LABEL,
			"link_type": "Page",
			"link_to": HOTEL_DASHBOARD_PAGE,
			"icon": "hotel",
			"hidden": 0,
			"is_query_report": 0,
			"onboard": 0,
			"link_count": 0,
		}
		ws.append("links", link_row)
		changed = True
	else:
		for row in ws.links or []:
			if row.type == "Link" and row.link_to == HOTEL_DASHBOARD_PAGE and not row.icon:
				row.icon = "hotel"
				changed = True

	try:
		blocks = json.loads(ws.content or "[]")
	except json.JSONDecodeError:
		blocks = []

	content_labels = {
		(block.get("data") or {}).get("shortcut_name")
		for block in blocks
		if block.get("type") == "shortcut" and (block.get("data") or {}).get("shortcut_name")
	}
	if HOTEL_DASHBOARD_SHORTCUT_LABEL not in content_labels:
		hotel_block = {
			"id": "fa-lnk-hotel-dashboard",
			"type": "shortcut",
			"data": {"shortcut_name": HOTEL_DASHBOARD_SHORTCUT_LABEL, "col": 4},
		}
		new_blocks = []
		inserted = False
		for block in blocks:
			new_blocks.append(block)
			if (
				not inserted
				and block.get("type") == "shortcut"
				and (block.get("data") or {}).get("shortcut_name") == "Asset Scan PWA"
			):
				new_blocks.append(hotel_block)
				inserted = True
		if not inserted:
			new_blocks = [hotel_block] + blocks
		ws.content = json.dumps(new_blocks)
		changed = True

	return changed


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
		],
		"Hotel Asset Register": [
			"System Manager",
			"Hotel Asset Admin",
			"Finance Asset Controller",
			"Auditor",
		],
		"Hotel NBV by Property": [
			"System Manager",
			"Hotel Asset Admin",
			"Finance Asset Controller",
			"Auditor",
		],
		"Hotel IAS 16 Disclosure Schedule": [
			"System Manager",
			"Hotel Asset Admin",
			"Finance Asset Controller",
			"Auditor",
		],
	}
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


def ensure_new_hotel_finance_reports():
	"""Import hotel IAS / valuation reports (idempotent)."""
	import os

	from frappe.modules.import_file import import_file_by_path

	base = os.path.join(frappe.get_app_path("omnexa_fixed_assets"), "omnexa_fixed_assets", "report")
	for folder in (
		"hotel_asset_register",
		"hotel_nbv_by_property",
		"hotel_ias_16_disclosure_schedule",
	):
		json_path = os.path.join(base, folder, f"{folder}.json")
		if os.path.exists(json_path):
			import_file_by_path(json_path, force=True, ignore_version=True)


def _disable_phantom_reports():
	"""Disable Script Report rows that have no Python implementation."""
	import os

	phantom = (
		"Claim Settlement Analysis",
		"Policy Renewal Forecast",
		"Insurance Cost Analysis",
		"Risk Exposure Report",
	)
	for name in phantom:
		if not frappe.db.exists("Report", name):
			continue
		scrub = frappe.scrub(name)
		py_path = os.path.join(
			frappe.get_app_path("omnexa_fixed_assets"),
			"omnexa_fixed_assets",
			"report",
			scrub,
			f"{scrub}.py",
		)
		if not os.path.exists(py_path):
			frappe.db.set_value("Report", name, "disabled", 1, update_modified=False)


def _remove_phantom_workspace_report_links():
	"""Drop workspace links to reports that were never implemented."""
	ws_name = "Fixed assets"
	if not frappe.db.exists("Workspace", ws_name):
		return
	phantom = {
		"Claim Settlement Analysis",
		"Policy Renewal Forecast",
		"Insurance Cost Analysis",
		"Risk Exposure Report",
	}
	ws = frappe.get_doc("Workspace", ws_name)
	changed = False
	for row in list(ws.links or []):
		if row.link_type == "Report" and row.link_to in phantom and not frappe.db.exists("Report", row.link_to):
			ws.links.remove(row)
			changed = True
	if changed:
		ws.save(ignore_permissions=True)


def refresh_hotel_vertical_from_company_activity():
	"""Hotel DocType fields, roles, report visibility, and Fixed Assets workspace links."""
	ensure_fixed_assets_workspace()
	ensure_fixed_assets_workspace_menus()
	ensure_hotel_assets_dashboard_page()
	ensure_new_hotel_finance_reports()
	_disable_phantom_reports()
	_remove_phantom_workspace_report_links()
	if not site_has_any_hotel_assets_company():
		return
	ensure_hotel_asset_management_custom_fields()
	ensure_hotel_roles()
	ensure_hotel_report_roles()


def company_on_save_sync_hotel_vertical(doc, method=None):
	"""After Company activity includes Hotel Assets, expose hotel shortcuts on `/app/fixed-assets`."""
	if getattr(frappe.flags, "in_test", False):
		return
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


def before_tests():
	from omnexa_core.omnexa_core.test_data import suppress_workflow_action_emails

	suppress_workflow_action_emails()
