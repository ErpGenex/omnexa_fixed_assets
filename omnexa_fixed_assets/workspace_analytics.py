# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Provision Dashboard Charts + Number Cards on Fixed Assets workspace.

Frappe desk widgets support Bar, Line, Pie, Donut, Percentage, Heatmap — not Power BI-style
waterfall / combo dual-axis. KPI-style tiles map to Number Card rows on the Workspace."""

from __future__ import annotations

import json

import frappe
from frappe import _

PALETTE = '{"colors": ["#2490ef", "#ffa00a", "#743ee2", "#5e64ff", "#39e4a5", "#fc6164"]}'


def _upsert_dashboard_chart(doc_dict: dict) -> None:
	name = doc_dict["chart_name"]
	if frappe.db.exists("Dashboard Chart", name):
		return
	doc = frappe.new_doc("Dashboard Chart")
	doc.update(doc_dict)
	doc.insert(ignore_permissions=True)


def _upsert_number_card(doc_dict: dict) -> None:
	label = doc_dict["label"]
	name = frappe.db.get_value("Number Card", {"label": label}, "name")
	if name:
		frappe.db.set_value("Number Card", name, {"is_public": 1}, update_modified=False)
		return
	doc = frappe.new_doc("Number Card")
	doc.update(doc_dict)
	doc.insert(ignore_permissions=True)
	frappe.db.set_value("Number Card", doc.name, {"is_public": 1}, update_modified=False)


def _ensure_chart_documents():
	_upsert_dashboard_chart(
		{
			"chart_name": "OMX FA — Assets by Status",
			"chart_type": "Group By",
			"document_type": "Fixed Asset",
			"filters_json": json.dumps([["docstatus", "<", 2]]),
			"group_by_based_on": "status",
			"group_by_type": "Count",
			"number_of_groups": 14,
			"type": "Donut",
			"is_public": 1,
			"custom_options": PALETTE,
		}
	)

	_upsert_dashboard_chart(
		{
			"chart_name": "OMX FA — Assets by Category",
			"chart_type": "Group By",
			"document_type": "Fixed Asset",
			"filters_json": json.dumps([["docstatus", "<", 2]]),
			"group_by_based_on": "category",
			"group_by_type": "Count",
			"number_of_groups": 14,
			"type": "Bar",
			"is_public": 1,
			"custom_options": PALETTE,
		}
	)

	if frappe.db.has_column("Fixed Asset", "hotel_property"):
		_upsert_dashboard_chart(
			{
				"chart_name": "OMX FA — Hotel Assets by Property",
				"chart_type": "Group By",
				"document_type": "Fixed Asset",
				"filters_json": json.dumps([["docstatus", "<", 2], ["hotel_property", "!=", ""]]),
				"group_by_based_on": "hotel_property",
				"group_by_type": "Count",
				"number_of_groups": 14,
				"type": "Bar",
				"is_public": 1,
				"custom_options": PALETTE,
			}
		)

	_upsert_dashboard_chart(
		{
			"chart_name": "OMX FA — Acquisitions Trend",
			"chart_type": "Count",
			"document_type": "Fixed Asset Acquisition",
			"filters_json": json.dumps([["docstatus", "<", 2]]),
			"timeseries": 1,
			"based_on": "posting_date",
			"timespan": "Last Year",
			"time_interval": "Monthly",
			"type": "Line",
			"is_public": 1,
			"custom_options": PALETTE,
		}
	)

	_upsert_dashboard_chart(
		{
			"chart_name": "OMX FA — Depreciation Entries Trend",
			"chart_type": "Count",
			"document_type": "Fixed Asset Depreciation Entry",
			"filters_json": json.dumps([["docstatus", "=", 1]]),
			"timeseries": 1,
			"based_on": "posting_date",
			"timespan": "Last Year",
			"time_interval": "Monthly",
			"type": "Line",
			"is_public": 1,
			"custom_options": PALETTE,
		}
	)


def _ensure_number_card_documents():
	_upsert_number_card(
		{
			"label": "OMX FA Total Active Assets",
			"type": "Document Type",
			"document_type": "Fixed Asset",
			"function": "Count",
			"filters_json": json.dumps([["docstatus", "<", 2]]),
			"is_public": 1,
			"show_percentage_stats": 0,
		}
	)

	if frappe.db.has_column("Fixed Asset", "net_book_value"):
		_upsert_number_card(
			{
				"label": "OMX FA Total Net Book Value",
				"type": "Document Type",
				"document_type": "Fixed Asset",
				"function": "Sum",
				"aggregate_function_based_on": "net_book_value",
				"filters_json": json.dumps([["docstatus", "<", 2]]),
				"is_public": 1,
				"show_percentage_stats": 0,
			}
		)

	if frappe.db.has_column("Fixed Asset", "hotel_property"):
		_upsert_number_card(
			{
				"label": "OMX FA Hotel-linked Assets",
				"type": "Document Type",
				"document_type": "Fixed Asset",
				"function": "Count",
				"filters_json": json.dumps([["docstatus", "<", 2], ["hotel_property", "!=", ""]]),
				"is_public": 1,
				"show_percentage_stats": 0,
			}
		)

	if frappe.db.exists("DocType", "Asset Alert"):
		_upsert_number_card(
			{
				"label": "OMX FA Open Asset Alerts",
				"type": "Document Type",
				"document_type": "Asset Alert",
				"function": "Count",
				"filters_json": json.dumps([["status", "=", "Open"]]),
				"is_public": 1,
				"show_percentage_stats": 0,
			}
		)


def _attach_to_workspace():
	ws_name = "Fixed Assets"
	if not frappe.db.exists("Workspace", ws_name):
		return

	ws = frappe.get_doc("Workspace", ws_name)

	chart_specs = [
		("OMX FA — Assets by Status", _("Assets by lifecycle status")),
		("OMX FA — Assets by Category", _("Assets by category")),
		("OMX FA — Acquisitions Trend", _("Acquisition documents over time")),
		("OMX FA — Depreciation Entries Trend", _("Posted depreciation trend")),
	]
	if frappe.db.has_column("Fixed Asset", "hotel_property"):
		chart_specs.insert(
			2,
			("OMX FA — Hotel Assets by Property", _("Hotel-linked assets by property")),
		)

	existing_charts = {row.chart_name for row in ws.charts}
	for chart_name, lbl in chart_specs:
		if frappe.db.exists("Dashboard Chart", chart_name) and chart_name not in existing_charts:
			ws.append("charts", {"chart_name": chart_name, "label": lbl})

	card_specs = [
		("OMX FA Total Active Assets", _("Total active assets")),
		("OMX FA Total Net Book Value", _("Total net book value")),
		("OMX FA Hotel-linked Assets", _("Hotel-linked assets")),
		("OMX FA Open Asset Alerts", _("Open asset alerts")),
	]
	existing_nc = {row.number_card_name for row in ws.number_cards}
	for nc_label, wlbl in card_specs:
		nc_name = frappe.db.get_value("Number Card", {"label": nc_label}, "name")
		if nc_name and nc_name not in existing_nc:
			ws.append("number_cards", {"number_card_name": nc_name, "label": wlbl})

	ws.save(ignore_permissions=True)


def ensure_fixed_assets_workspace_analytics():
	"""Create standard Dashboard Charts / Number Cards and attach them to workspace Fixed Assets."""
	if not frappe.db.exists("Workspace", "Fixed Assets"):
		return

	try:
		_ensure_chart_documents()
		_ensure_number_card_documents()
		_attach_to_workspace()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ensure_fixed_assets_workspace_analytics failed")


def attach_analytics_bundle(workspace_name: str, chart_names: list[tuple[str, str]], number_card_labels: list[tuple[str, str]]):
	"""Reuse charts/cards on another Workspace (manual / scripting).

	:param workspace_name: Workspace.name (label)
	:param chart_names: list of (Dashboard Chart name, workspace row label)
	:param number_card_labels: list of (Number Card.label, workspace row label)
	"""
	if not frappe.db.exists("Workspace", workspace_name):
		frappe.throw(_("Workspace {0} not found.").format(workspace_name))

	ws = frappe.get_doc("Workspace", workspace_name)
	existing_charts = {row.chart_name for row in ws.charts}
	for chart_name, lbl in chart_names:
		if frappe.db.exists("Dashboard Chart", chart_name) and chart_name not in existing_charts:
			ws.append("charts", {"chart_name": chart_name, "label": lbl})

	existing_nc = {row.number_card_name for row in ws.number_cards}
	for nc_label, wlbl in number_card_labels:
		nc_name = frappe.db.get_value("Number Card", {"label": nc_label}, "name")
		if nc_name and nc_name not in existing_nc:
			ws.append("number_cards", {"number_card_name": nc_name, "label": wlbl})

	ws.save(ignore_permissions=True)
