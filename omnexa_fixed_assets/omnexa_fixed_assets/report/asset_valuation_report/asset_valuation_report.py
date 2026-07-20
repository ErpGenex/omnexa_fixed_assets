# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))
	conditions = ["company = %(company)s"]
	if filters.get("branch"):
		conditions.append("branch = %(branch)s")

	data = frappe.db.sql(
		f"""
		SELECT
			name AS fixed_asset,
			asset_name,
			category,
			acquisition_cost,
			accumulated_depreciation,
			net_book_value
		FROM `tabFixed Asset`
		WHERE {' AND '.join(conditions)}
		ORDER BY net_book_value DESC
		""",
		filters,
		as_dict=True,
	)
	columns = [
		{"label": _("Asset"), "fieldname": "fixed_asset", "fieldtype": "Link", "options": "Fixed Asset", "width": 150},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180},
		{"label": _("Category"), "fieldname": "category", "fieldtype": "Link", "options": "Fixed Asset Category", "width": 150},
		{"label": _("Acquisition Cost"), "fieldname": "acquisition_cost", "fieldtype": "Currency", "width": 140},
		{"label": _("Accum. Depreciation"), "fieldname": "accumulated_depreciation", "fieldtype": "Currency", "width": 140},
		{"label": _("Net Book Value"), "fieldname": "net_book_value", "fieldtype": "Currency", "width": 140},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart