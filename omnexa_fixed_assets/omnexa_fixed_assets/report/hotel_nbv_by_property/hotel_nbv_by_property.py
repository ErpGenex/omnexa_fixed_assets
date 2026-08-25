# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""IAS 16 — hotel property-level NBV roll-up (component / CGU disclosure)."""

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
		frappe.throw(_("Company is required."), title=_("Filters"))

	params = {"company": filters.company}
	conditions = [
		"fa.company = %(company)s",
		"IFNULL(fa.hotel_property, '') != ''",
	]
	if filters.get("branch"):
		params["branch"] = filters.branch
		conditions.append("fa.branch = %(branch)s")
	if filters.get("hotel_property"):
		params["hotel_property"] = filters.hotel_property
		conditions.append("fa.hotel_property = %(hotel_property)s")

	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return _columns(), []
		params["allowed_branches"] = tuple(allowed)
		conditions.append("fa.branch IN %(allowed_branches)s")

	data = frappe.db.sql(
		f"""
		SELECT
			fa.hotel_property,
			fa.branch,
			COUNT(*) AS asset_count,
			COALESCE(SUM(fa.acquisition_cost), 0) AS gross_carrying_amount,
			COALESCE(SUM(fa.accumulated_depreciation), 0) AS accumulated_depreciation,
			COALESCE(SUM(fa.net_book_value), 0) AS net_book_value
		FROM `tabFixed Asset` fa
		WHERE {" AND ".join(conditions)}
		GROUP BY fa.hotel_property, fa.branch
		ORDER BY net_book_value DESC, fa.hotel_property
		""",
		params,
		as_dict=True,
	)
	for row in data:
		row["gross_carrying_amount"] = flt(row.gross_carrying_amount)
		row["accumulated_depreciation"] = flt(row.accumulated_depreciation)
		row["net_book_value"] = flt(row.net_book_value)

	columns = _columns()
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart


def _columns():
	return [
		{"label": _("Hotel Property"), "fieldname": "hotel_property", "fieldtype": "Link", "options": "Hotel Property", "width": 200},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
		{"label": _("Assets"), "fieldname": "asset_count", "fieldtype": "Int", "width": 90},
		{"label": _("Gross Carrying Amount"), "fieldname": "gross_carrying_amount", "fieldtype": "Currency", "width": 150},
		{"label": _("Accumulated Depreciation"), "fieldname": "accumulated_depreciation", "fieldtype": "Currency", "width": 160},
		{"label": _("Net Book Value"), "fieldname": "net_book_value", "fieldtype": "Currency", "width": 140},
	]
