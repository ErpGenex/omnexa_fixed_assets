# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""IAS 16 asset-level disclosure schedule scoped to hotel-linked fixed assets."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from omnexa_core.omnexa_core.branch_access import get_allowed_branches
from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled
from omnexa_fixed_assets.utils.report_filters import merge_navbar_report_filters


def execute(filters=None):
	enforce_hotel_feature_enabled()
	filters = merge_navbar_report_filters(filters)
	if not filters.get("company"):
		frappe.throw(_("Company is required"))

	conditions = [
		"fa.company = %(company)s",
		"IFNULL(fa.hotel_property, '') != ''",
	]
	if filters.get("branch"):
		conditions.append("fa.branch = %(branch)s")
	if filters.get("category"):
		conditions.append("fa.category = %(category)s")
	if filters.get("status"):
		conditions.append("fa.status = %(status)s")
	if filters.get("hotel_property"):
		conditions.append("fa.hotel_property = %(hotel_property)s")

	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return _columns(), []
		filters.allowed_branches = tuple(allowed)
		conditions.append("fa.branch IN %(allowed_branches)s")

	data = frappe.db.sql(
		f"""
		SELECT
			fa.name,
			fa.asset_name,
			fa.hotel_property,
			fa.hotel_room,
			fa.category,
			fa.branch,
			fa.status,
			fa.capitalization_date AS acquisition_date,
			COALESCE(fa.acquisition_cost, 0) AS acquisition_cost,
			COALESCE(fa.accumulated_depreciation, 0) AS accumulated_depreciation,
			COALESCE(fa.net_book_value, 0) AS net_book_value
		FROM `tabFixed Asset` fa
		WHERE {" AND ".join(conditions)}
		ORDER BY fa.hotel_property, fa.category, fa.asset_name
		""",
		filters,
		as_dict=True,
	)
	for row in data:
		for field in ("acquisition_cost", "accumulated_depreciation", "net_book_value"):
			row[field] = flt(row[field])

	columns = _columns()
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart


def _columns():
	return [
		{"label": _("Asset"), "fieldname": "name", "fieldtype": "Link", "options": "Fixed Asset", "width": 130},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 160},
		{"label": _("Hotel Property"), "fieldname": "hotel_property", "fieldtype": "Link", "options": "Hotel Property", "width": 170},
		{"label": _("Room"), "fieldname": "hotel_room", "fieldtype": "Link", "options": "Hotel Room", "width": 120},
		{"label": _("Category"), "fieldname": "category", "fieldtype": "Link", "options": "Fixed Asset Category", "width": 140},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": _("Acquisition Date"), "fieldname": "acquisition_date", "fieldtype": "Date", "width": 110},
		{"label": _("Cost"), "fieldname": "acquisition_cost", "fieldtype": "Currency", "width": 120},
		{"label": _("Accum. Depreciation"), "fieldname": "accumulated_depreciation", "fieldtype": "Currency", "width": 130},
		{"label": _("NBV"), "fieldname": "net_book_value", "fieldtype": "Currency", "width": 120},
	]
