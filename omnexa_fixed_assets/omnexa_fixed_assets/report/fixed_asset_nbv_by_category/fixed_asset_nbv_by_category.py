# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import flt
from omnexa_core.omnexa_core.branch_access import get_allowed_branches


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))

	conditions = ["fa.company = %(company)s"]
	if filters.get("branch"):
		conditions.append("fa.branch = %(branch)s")
	if filters.get("category"):
		conditions.append("fa.category = %(category)s")

	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return _columns(), []
		filters.allowed_branches = tuple(allowed)
		conditions.append("fa.branch in %(allowed_branches)s")

	data = frappe.db.sql(
		f"""
		SELECT
			fa.branch,
			fa.category,
			COUNT(*) AS asset_count,
			COALESCE(SUM(fa.acquisition_cost), 0) AS acquisition_cost,
			COALESCE(SUM(fa.accumulated_depreciation), 0) AS accumulated_depreciation,
			COALESCE(SUM(fa.net_book_value), 0) AS net_book_value
		FROM `tabFixed Asset` fa
		WHERE {' AND '.join(conditions)}
		GROUP BY fa.branch, fa.category
		ORDER BY fa.branch, net_book_value DESC
		""",
		filters,
		as_dict=True,
	)

	for row in data:
		row["acquisition_cost"] = flt(row.acquisition_cost)
		row["accumulated_depreciation"] = flt(row.accumulated_depreciation)
		row["net_book_value"] = flt(row.net_book_value)
	columns = _columns()
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart


def _columns():
	return [
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 130},
		{"label": _("Category"), "fieldname": "category", "fieldtype": "Link", "options": "Fixed Asset Category", "width": 180},
		{"label": _("Assets"), "fieldname": "asset_count", "fieldtype": "Int", "width": 90},
		{"label": _("Acquisition Cost"), "fieldname": "acquisition_cost", "fieldtype": "Currency", "width": 140},
		{"label": _("Accumulated Depreciation"), "fieldname": "accumulated_depreciation", "fieldtype": "Currency", "width": 170},
		{"label": _("Net Book Value"), "fieldname": "net_book_value", "fieldtype": "Currency", "width": 140},
	]
