# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Full Fixed Assets workspace — SAP SD / Van Sales parity catalog."""

from __future__ import annotations

import json

import frappe

from omnexa_core.omnexa_core.vertical_workspace_sync import (
	build_link_rows_for_app,
	drop_missing_workspace_dashboard_links,
)

WorkspaceLink = tuple[str, str, str]

WORKSPACE_NAME = "Fixed Assets"

_SHORTCUT_COLORS = ("Blue", "Green", "Orange", "Red", "Cyan", "Purple", "Teal", "Pink", "Yellow")

_DASHBOARD_PAGES: list[WorkspaceLink] = [
	("Page", "fixed-assets-workcenter", "Fixed Assets Workcenter"),
	("Page", "fa-executive-dashboard", "Executive Dashboard"),
	("Page", "fixed-assets-analytics-dashboard", "Analytics Dashboard"),
	("Page", "fixed-assets-operations-desk", "Operations Desk"),
	("Page", "fixed-assets-finance-desk", "Finance Desk"),
	("Page", "fa-hotel-assets-dashboard", "Hotel Assets Dashboard"),
	("Page", "fa-hospitality-command-center", "Hospitality Command Center"),
	("Page", "fa-global-hospitality-portfolio", "Global Hospitality Portfolio"),
	("Page", "fa-live-asset-tracking", "Live Asset Tracking"),
	("Page", "fa-linen-dashboard", "Linen Dashboard"),
	("Page", "fa-asset-wizards", "Asset Lifecycle Wizards"),
	("Page", "fa-asset-scan-pwa", "Asset Scan PWA"),
	("Page", "fixed-assets-customer-portal", "Customer Portal"),
]

_HOTEL_SETUP: list[WorkspaceLink] = [
	("DocType", "Hotel Property", "Hotel Property"),
	("DocType", "Hotel Functional Area", "Hotel Functional Area"),
	("DocType", "Hotel Room", "Hotel Room"),
	("DocType", "Hotel Floor Plan", "Hotel Floor Plan"),
]

_HOTEL_OPERATIONS: list[WorkspaceLink] = [
	("DocType", "RFID Gateway", "RFID Gateway"),
	("DocType", "RFID Reader", "RFID Reader"),
	("DocType", "RFID Scan Log", "RFID Scan Log"),
	("DocType", "Hotel Asset Inspection", "Hotel Asset Inspection"),
	("DocType", "Hotel Asset Transfer", "Hotel Asset Transfer"),
	("DocType", "Hospitality Audit Event", "Hospitality Audit Event"),
	("DocType", "Asset Lifecycle Wizard Session", "Wizard Sessions"),
]

_LINEN_MANAGEMENT: list[WorkspaceLink] = [
	("DocType", "Linen Item", "Linen Item"),
	("DocType", "Linen Movement", "Linen Movement"),
	("DocType", "Linen Laundry Cycle", "Linen Laundry Cycle"),
	("DocType", "Linen Issue Batch", "Linen Issue Batch"),
	("DocType", "Linen Shortage Alert", "Linen Shortage Alert"),
	("Report", "Missing Linen", "Missing Linen"),
]

_HOTEL_MAINTENANCE: list[WorkspaceLink] = [
	("DocType", "Asset Work Order", "Asset Work Order"),
	("DocType", "Fixed Asset Maintenance", "Fixed Asset Maintenance"),
	("DocType", "Asset Failure Event", "Asset Failure Event"),
	("DocType", "Fixed Asset Inspection", "Fixed Asset Inspection"),
	("DocType", "Asset Alert", "Asset Alert"),
]

_HOTEL_FINANCE_REPORTS: list[WorkspaceLink] = [
	("Report", "Asset Valuation Report", "Asset Valuation Report"),
	("Report", "Replacement Forecast Report", "Replacement Forecast Report"),
	("Report", "Inspection Compliance Report", "Inspection Compliance Report"),
	("Report", "Fixed Asset NBV by Category", "Fixed Asset NBV by Category"),
	("Report", "Asset Health Report", "Asset Health Report"),
]

_HOTEL_REPORTS: list[WorkspaceLink] = [
	("Report", "Assets by Room", "Assets by Room"),
	("Report", "Hotel Assets by Floor", "Hotel Assets by Floor"),
	("Report", "Hotel Operational Asset Status", "Hotel Operational Asset Status"),
	("Report", "Hotel Inspection Summary", "Hotel Inspection Summary"),
	("Report", "Missing Assets", "Missing Assets"),
	("Report", "Last Seen Assets", "Last Seen Assets"),
	("Report", "Unscanned Assets", "Unscanned Assets"),
	("Report", "Hotel Movement History", "Hotel Movement History"),
	("Report", "Hotel Asset Depreciation", "Hotel Asset Depreciation"),
	("Report", "Warranty Expiring Assets", "Warranty Expiring"),
]

# Exported for install.py — hotel DocType/report sections (pages live under Dashboards).
HOTEL_WORKSPACE_SECTIONS: list[tuple[str, list[WorkspaceLink]]] = [
	("🏨 Hotel Setup", _HOTEL_SETUP),
	("🏨 Hotel Operations", _HOTEL_OPERATIONS),
	("🛏️ Linen Management", _LINEN_MANAGEMENT),
	("🔧 Hotel Maintenance & Quality", _HOTEL_MAINTENANCE),
	("📈 Hotel Finance & Forecasting", _HOTEL_FINANCE_REPORTS),
	("📈 Hotel Reports", _HOTEL_REPORTS),
]

WORKSPACE_SECTIONS: list[tuple[str, list[WorkspaceLink]]] = [
	("📊 Dashboards", _DASHBOARD_PAGES),
	("📋 Policy & register", [
		("DocType", "Fixed Asset Category", "Category"),
		("DocType", "Fixed Asset", "Fixed Asset"),
		("DocType", "Fixed Asset Location", "Location"),
	]),
	("💰 Recognition & depreciation", [
		("DocType", "Fixed Asset Acquisition", "Acquisition"),
		("DocType", "Fixed Asset Depreciation Entry", "Depreciation Entry"),
		("DocType", "Fixed Asset Revaluation", "Revaluation"),
	]),
	("🔄 Transfers & disposal", [
		("DocType", "Fixed Asset Transfer", "Transfer"),
		("DocType", "Fixed Asset Disposal", "Disposal"),
		("DocType", "Fixed Asset Write-Off", "Write-Off"),
	]),
	("🔧 Assurance", [
		("DocType", "Fixed Asset Maintenance", "Maintenance"),
		("DocType", "Fixed Asset Inspection", "Inspection"),
		("DocType", "Fixed Asset Movement Log", "Movement Log"),
	]),
	("📈 Reports · Register", [
		("Report", "Asset Register Report", "Asset Register"),
		("Report", "Asset Valuation Report", "Valuation"),
		("Report", "Fixed Asset Summary", "Summary"),
	]),
	("📈 Reports · Depreciation", [
		("Report", "Asset Depreciation Schedule", "Depreciation Schedule"),
		("Report", "Fixed Asset NBV by Category", "NBV by Category"),
		("Report", "Asset Movement Report", "Movement"),
	]),
	("💰 Finance", [
		("DocType", "Journal Entry", "Journal Entry"),
		("DocType", "GL Account", "GL Account"),
	]),
	*HOTEL_WORKSPACE_SECTIONS,
]

_REMOVED_SECTIONS = [
	(
		"📊 Dashboards & Mobile",
		[
			("Page", "fa-executive-dashboard", "Executive Dashboard"),
			("Page", "fa-van-sales-pwa", "Van Sales PWA"),
		],
	),
	(
		"🏢 Organization & Network",
		[
			("DocType", "Omnexa Sales Settings", "Sales Settings"),
			("DocType", "Customer Profile", "Customer Profile"),
			("DocType", "Customer", "Customer"),
			("DocType", "Distribution Zone", "Distribution Zone"),
			("DocType", "Fixed Assets Vehicle", "Fixed Assets Vehicle"),
			("DocType", "Fixed Assets Sales Representative", "Sales Representative"),
		],
	),
	(
		"🚚 Field Sales & Distribution",
		[
			("DocType", "Fixed Assets Route Plan", "Route Plan"),
			("DocType", "Fixed Assets Distribution Order", "Distribution Order"),
			("DocType", "Fixed Assets Van Sales Invoice", "Van Sales Invoice"),
			("DocType", "Fixed Assets Vehicle Stock Transfer", "Vehicle Stock Transfer"),
		],
	),
	(
		"💰 Commissions & Incentives",
		[
			("DocType", "Fixed Assets Commission Rule", "Commission Rule"),
			("DocType", "Fixed Assets Commission Settlement", "Commission Settlement"),
		],
	),
	(
		"📋 Tenders & Credit",
		[
			("DocType", "Fixed Assets Tender", "Tender"),
			("DocType", "Fixed Assets Installment Contract", "Installment Contract"),
		],
	),
	(
		"💳 Finance & ERP",
		[
			("DocType", "Sales Invoice", "Sales Invoice"),
			("DocType", "Payment Entry", "Payment Entry"),
			("DocType", "Journal Entry", "Journal Entry"),
			("DocType", "GL Account", "GL Account"),
			("DocType", "Cost Center", "Cost Center"),
		],
	),
	(
		"📈 Reports · Sales & Routes",
		[
			("Report", "Fixed Assets Sales Summary", "Sales Summary"),
			("Report", "Fixed Assets Distribution Fulfillment", "Distribution Fulfillment"),
			("Report", "Fixed Assets Vehicle Transfer Summary", "Vehicle Transfer Summary"),
			("Report", "Fixed Assets Route Efficiency", "Route Efficiency"),
			("Report", "Fixed Assets Rep Target Tracking", "Rep Target Tracking"),
		],
	),
	(
		"📈 Reports · Commissions & Pipeline",
		[
			("Report", "Fixed Assets Commission Summary", "Commission Summary"),
			("Report", "Fixed Assets Tender Pipeline", "Tender Pipeline"),
			("Report", "Fixed Assets Installment Portfolio", "Installment Portfolio"),
		],
	),
	(
		"📈 Reports · Finance & POS",
		[
			("Report", "POS Z Report Reconciliation", "POS Z Reconciliation"),
			("Report", "Sales Register", "Sales Register"),
			("Report", "Customer Ledger", "Customer Ledger"),
			("Report", "General Ledger", "General Ledger"),
		],
	),
]


def _link_exists(link_type: str, link_to: str) -> bool:
	if link_type == "DocType":
		return bool(frappe.db.exists("DocType", link_to))
	if link_type == "Report":
		return bool(frappe.db.exists("Report", link_to))
	if link_type == "Page":
		return bool(frappe.db.exists("Page", link_to))
	return False


def _build_link_rows() -> list[dict]:
	return build_link_rows_for_app("omnexa_fixed_assets", WORKSPACE_SECTIONS)


def _build_shortcuts(link_rows: list[dict]) -> list[dict]:
	shortcuts: list[dict] = []
	idx = 0
	priority_types = ("Page", "DocType", "Report", "Dashboard")
	links = [r for r in link_rows if r.get("type") == "Link"]
	for lt in priority_types:
		for row in links:
			if row.get("link_type") != lt:
				continue
			entry = {
				"label": row["label"],
				"link_to": row["link_to"],
				"type": row["link_type"],
				"color": _SHORTCUT_COLORS[idx % len(_SHORTCUT_COLORS)]
	}
			if lt == "DocType":
				entry["doc_view"] = "List"
			if lt == "Report" and row.get("report_ref_doctype"):
				entry["report_ref_doctype"] = row["report_ref_doctype"]
			shortcuts.append(entry)
			idx += 1
	return shortcuts


def _onboarding_blocks(existing_content: str | None) -> list[dict]:
	if not existing_content:
		return []
	try:
		blocks = json.loads(existing_content)
	except json.JSONDecodeError:
		return []
	return [b for b in blocks if b.get("type") == "onboarding"]


def _build_content(link_rows: list[dict], ws) -> str:
	content: list[dict] = []
	content.extend(_onboarding_blocks(ws.content))
	content.append(
		{
			"id": "fa-title",
			"type": "header",
			"data": {"text": '<span class="h4"><b>Fixed Assets</b></span>', "col": 12}
	}
	)
	section_idx = 0
	link_idx = 0
	for row in link_rows:
		if row.get("type") == "Card Break":
			if section_idx:
				content.append({"id": f"fa-sp-{section_idx
	}", "type": "spacer", "data": {"col": 12}
	})
			content.append(
				{
					"id": f"fa-sec-{section_idx
	}",
					"type": "header",
					"data": {"text": f'<span class="h5"><b>{row["label"]
	}</b></span>', "col": 12}
	}
			)
			section_idx += 1
			continue
		content.append(
			{
				"id": f"fa-lnk-{link_idx
	}",
				"type": "shortcut",
				"data": {"shortcut_name": row["label"], "col": 4}
	}
		)
		link_idx += 1

	if ws.number_cards:
		content.append({"id": "fa-kpi-sp", "type": "spacer", "data": {"col": 12}
	})
		content.append(
			{
				"id": "fa-kpi-h",
				"type": "header",
				"data": {"text": '<span class="h5"><b>📊 KPIs</b></span>', "col": 12}
	}
		)
		for idx, nc in enumerate(ws.number_cards):
			content.append(
				{
					"id": f"fa-nc-{idx
	}",
					"type": "number_card",
					"data": {"number_card_name": nc.number_card_name, "col": 4}
	}
			)

	if ws.charts:
		content.append({"id": "fa-ch-sp", "type": "spacer", "data": {"col": 12}
	})
		content.append(
			{
				"id": "fa-ch-h",
				"type": "header",
				"data": {"text": '<span class="h5"><b>📈 Charts</b></span>', "col": 12}
	}
		)
		for idx, ch in enumerate(ws.charts):
			content.append(
				{
					"id": f"fa-ch-{idx
	}",
					"type": "chart",
					"data": {"chart_name": ch.label or ch.chart_name, "col": 4}
	}
			)

	return json.dumps(content, separators=(",", ":"))


def sync_fa_workspace_menu(*, save: bool = True, rebuild: bool = True) -> dict:
	stats = {"sections": 0, "links": 0, "shortcuts": 0
	}
	if not frappe.db.exists("Workspace", WORKSPACE_NAME):
		return stats
	rows = _build_link_rows()
	link_rows = [r for r in rows if r.get("type") == "Link"]
	new_shortcuts = _build_shortcuts(rows)
	ws = frappe.get_doc("Workspace", WORKSPACE_NAME)
	if rebuild:
		ws.set("links", [])
		ws.set("shortcuts", [])
	for row in rows:
		if row["type"] == "Card Break":
			stats["sections"] += 1
		else:
			stats["links"] += 1
		ws.append("links", row)
	for sc in new_shortcuts:
		ws.append("shortcuts", sc)
	stats["shortcuts"] = len(new_shortcuts)
	drop_missing_workspace_dashboard_links(ws)
	ws.content = _build_content(rows, ws)
	stats["content_blocks"] = len(json.loads(ws.content))
	if save:
		ws.flags.ignore_permissions = True
		ws.flags.ignore_version = True
		latest = frappe.db.get_value("Workspace", WORKSPACE_NAME, "modified")
		if latest:
			ws._original_modified = latest
		ws.save()
		frappe.clear_cache(doctype="Workspace")
	stats["total_links"] = len(link_rows)
	return stats


@frappe.whitelist()
def get_workspace_coverage() -> dict:
	rows = _build_link_rows()
	link_rows = [r for r in rows if r.get("type") == "Link"]
	return {
		"sections": len([r for r in rows if r.get("type") == "Card Break"]),
		"links_catalogued": len(link_rows)
	}
