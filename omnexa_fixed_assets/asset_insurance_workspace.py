# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Dashboard charts + Number Cards for the packaged **Asset Insurance** workspace."""

from __future__ import annotations

import json

import frappe

PALETTE = '{"colors": ["#2490ef", "#ffa00a", "#743ee2", "#5e64ff", "#39e4a5", "#fc6164"]}'

_MODULE = "Omnexa Fixed Assets"


def _upsert_dashboard_chart(doc_dict: dict) -> None:
	"""Insert or update; ``filters_json`` must be 4-tuples (doctype, field, op, value) for Desk chart widgets."""
	name = doc_dict["chart_name"]
	payload = {k: v for k, v in doc_dict.items() if k != "chart_name"}
	if frappe.db.exists("Dashboard Chart", name):
		doc = frappe.get_doc("Dashboard Chart", name)
		doc.update(payload)
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.new_doc("Dashboard Chart")
		doc.update(doc_dict)
		doc.insert(ignore_permissions=True)


def _upsert_number_card_named(name: str, fields: dict) -> None:
	"""Insert or update Number Card; filters use 4-tuple rows for ``get_result`` / route_options."""
	if frappe.db.exists("Number Card", name):
		doc = frappe.get_doc("Number Card", name)
		doc.update(fields)
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.new_doc("Number Card")
		doc.update(fields)
		doc.insert(ignore_permissions=True, set_name=name)


def ensure_asset_insurance_dashboard_charts() -> None:
	if not frappe.db.exists("DocType", "Insurance Policy"):
		return

	_upsert_dashboard_chart(
		{
			"chart_name": "OMX FA INS — Policies by status",
			"chart_type": "Group By",
			"document_type": "Insurance Policy",
			"filters_json": json.dumps([["Insurance Policy", "docstatus", "=", 1]]),
			"group_by_based_on": "policy_status",
			"group_by_type": "Count",
			"number_of_groups": 14,
			"type": "Donut",
			"is_public": 1,
			"custom_options": PALETTE,
		}
	)
	_upsert_dashboard_chart(
		{
			"chart_name": "OMX FA INS — Claims by status",
			"chart_type": "Group By",
			"document_type": "Insurance Claim",
			"filters_json": json.dumps([["Insurance Claim", "docstatus", "=", 1]]),
			"group_by_based_on": "claim_status",
			"group_by_type": "Count",
			"number_of_groups": 14,
			"type": "Donut",
			"is_public": 1,
			"custom_options": PALETTE,
		}
	)
	_upsert_dashboard_chart(
		{
			"chart_name": "OMX FA INS — Policies by coverage",
			"chart_type": "Group By",
			"document_type": "Insurance Policy",
			"filters_json": json.dumps([["Insurance Policy", "docstatus", "=", 1]]),
			"group_by_based_on": "coverage_type",
			"group_by_type": "Count",
			"number_of_groups": 20,
			"type": "Bar",
			"is_public": 1,
			"custom_options": PALETTE,
		}
	)
	_upsert_dashboard_chart(
		{
			"chart_name": "OMX FA INS — Claims filed trend",
			"chart_type": "Count",
			"document_type": "Insurance Claim",
			"filters_json": json.dumps([["Insurance Claim", "docstatus", "<", 2]]),
			"timeseries": 1,
			"based_on": "claim_date",
			"timespan": "Last Year",
			"time_interval": "Monthly",
			"type": "Line",
			"is_public": 1,
			"custom_options": PALETTE,
		}
	)
	_upsert_dashboard_chart(
		{
			"chart_name": "OMX FA INS — New policies trend",
			"chart_type": "Count",
			"document_type": "Insurance Policy",
			"filters_json": json.dumps([["Insurance Policy", "docstatus", "<", 2]]),
			"timeseries": 1,
			"based_on": "posting_date",
			"timespan": "Last Year",
			"time_interval": "Monthly",
			"type": "Line",
			"is_public": 1,
			"custom_options": PALETTE,
		}
	)


def ensure_asset_insurance_number_cards() -> None:
	if not frappe.db.exists("DocType", "Insurance Policy") or not frappe.db.exists("DocType", "Insurance Claim"):
		return

	_upsert_number_card_named(
		"Submitted Policies",
		{
			"label": "Submitted Policies",
			"type": "Document Type",
			"document_type": "Insurance Policy",
			"function": "Count",
			"filters_json": json.dumps([["Insurance Policy", "docstatus", "=", 1]]),
			"module": _MODULE,
			"is_public": 1,
			"show_percentage_stats": 1,
			"stats_time_interval": "Monthly",
			"show_full_number": 1,
		},
	)
	_upsert_number_card_named(
		"Active Policies",
		{
			"label": "Active Policies",
			"type": "Document Type",
			"document_type": "Insurance Policy",
			"function": "Count",
			"filters_json": json.dumps(
				[
					["Insurance Policy", "docstatus", "=", 1],
					["Insurance Policy", "policy_status", "=", "Active"],
				]
			),
			"module": _MODULE,
			"is_public": 1,
			"show_percentage_stats": 1,
			"stats_time_interval": "Monthly",
			"show_full_number": 1,
		},
	)
	_upsert_number_card_named(
		"Open Claims",
		{
			"label": "Open Claims",
			"type": "Document Type",
			"document_type": "Insurance Claim",
			"function": "Count",
			"filters_json": json.dumps(
				[
					["Insurance Claim", "docstatus", "=", 1],
					["Insurance Claim", "claim_status", "=", "Open"],
				]
			),
			"module": _MODULE,
			"is_public": 1,
			"show_percentage_stats": 1,
			"stats_time_interval": "Monthly",
			"show_full_number": 1,
		},
	)
	_upsert_number_card_named(
		"Annual Premium",
		{
			"label": "Annual Premium",
			"type": "Document Type",
			"document_type": "Insurance Policy",
			"function": "Sum",
			"aggregate_function_based_on": "annual_premium",
			"filters_json": json.dumps(
				[
					["Insurance Policy", "docstatus", "=", 1],
					["Insurance Policy", "policy_status", "=", "Active"],
				]
			),
			"module": _MODULE,
			"is_public": 1,
			"show_percentage_stats": 0,
			"show_full_number": 1,
		},
	)


def ensure_asset_insurance_desk_permissions() -> None:
	"""Let typical desk roles see charts/KPI tiles (``get_desktop_page`` checks DocType + Report ACL)."""
	from frappe.permissions import add_permission

	for role in ("Desk User", "Accounts User"):
		try:
			add_permission("Dashboard Chart", role, permlevel=0, ptype="read")
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Omnexa: add_permission Dashboard Chart / {role}")
		try:
			add_permission("Number Card", role, permlevel=0, ptype="read")
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Omnexa: add_permission Number Card / {role}")


def ensure_asset_insurance_desk_artifacts() -> None:
	"""Idempotent: charts + KPI Number Cards referenced by the packaged workspace."""
	ensure_asset_insurance_dashboard_charts()
	ensure_asset_insurance_number_cards()


def ensure_asset_insurance_on_fixed_assets_workspace() -> None:
	"""Link **Asset Insurance** on Fixed Assets desk + correct ``parent_page`` for sidebar nesting."""
	if not frappe.db.exists("Workspace", "Fixed Assets") or not frappe.db.exists("Workspace", "Asset Insurance"):
		return

	try:
		from omnexa_core.omnexa_core.workspace_control_tower import _ensure_asset_insurance_workspace

		_ensure_asset_insurance_workspace()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa: _ensure_asset_insurance_workspace")

	ws = frappe.get_doc("Workspace", "Fixed Assets")
	url = "/app/asset-insurance"
	has_shortcut = any(
		(row.get("type") == "URL" and ((row.get("url") or row.get("link_to") or "").strip() == url))
		for row in (ws.shortcuts or [])
	)
	changed = False
	if not has_shortcut:
		ws.append(
			"shortcuts",
			{
				"type": "URL",
				"url": url,
				"label": "Asset Insurance",
				"color": "Blue",
				"doc_view": "",
			},
		)
		changed = True

	has_policy_link = any(
		row.get("type") == "Link"
		and row.get("link_type") == "DocType"
		and (row.get("link_to") or "").strip() == "Insurance Policy"
		for row in (ws.links or [])
	)
	if frappe.db.exists("DocType", "Insurance Policy") and not has_policy_link:
		ws.append(
			"links",
			{
				"type": "Link",
				"hidden": 0,
				"onboard": 0,
				"label": "Insurance Policy",
				"link_type": "DocType",
				"link_to": "Insurance Policy",
				"link_count": 0,
				"icon": "shield",
			},
		)
		changed = True

	if changed:
		ws.save(ignore_permissions=True)

	# Nest directly under Fixed Assets in the sidebar (first child, right after parent sequence).
	ai = frappe.get_doc("Workspace", "Asset Insurance")
	ai_updates: dict[str, object] = {}
	parent = "Fixed Assets"
	if (ai.parent_page or "").strip() != parent:
		ai_updates["parent_page"] = parent
	if not ai.public:
		ai_updates["public"] = 1
	if ai.is_hidden:
		ai_updates["is_hidden"] = 0
	if (ai.icon or "").strip() in ("", "shield"):
		ai_updates["icon"] = "es-line-shield"
	if ai_updates:
		for field, value in ai_updates.items():
			setattr(ai, field, value)
		ai.save(ignore_permissions=True)
	if float(frappe.db.get_value("Workspace", "Asset Insurance", "sequence_id") or 0) != 3.1:
		frappe.db.set_value("Workspace", "Asset Insurance", "sequence_id", 3.1, update_modified=False)


def refresh_asset_insurance_workspace() -> None:
	"""Re-apply control-tower layout after DocTypes/reports exist."""
	if not frappe.db.exists("DocType", "Insurance Policy"):
		return
	from omnexa_core.omnexa_core.workspace_control_tower import sync_workspace_for_app

	sync_workspace_for_app("omnexa_fixed_assets_insurance")


def bootstrap_asset_insurance_desk() -> None:
	"""Called from ``after_migrate`` once insurance DocTypes are on the site."""
	ensure_asset_insurance_desk_permissions()
	ensure_asset_insurance_desk_artifacts()
	refresh_asset_insurance_workspace()
