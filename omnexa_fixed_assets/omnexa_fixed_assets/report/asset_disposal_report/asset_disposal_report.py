# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	conditions = ["d.company = %(company)s", "d.docstatus = 1"]
	if filters.get("from_date"):
		conditions.append("d.disposal_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("d.disposal_date <= %(to_date)s")

	data = frappe.db.sql(
		f"""
		SELECT
			d.name,
			d.disposal_date,
			d.fixed_asset,
			d.carrying_amount_snapshot,
			d.proceeds,
			(d.proceeds - d.carrying_amount_snapshot) AS gain_or_loss,
			d.branch
		FROM `tabFixed Asset Disposal` d
		WHERE {' AND '.join(conditions)}
		ORDER BY d.disposal_date DESC, d.name DESC
		""",
		filters,
		as_dict=True,
	)
	columns = [
		{"label": _("Disposal"), "fieldname": "name", "fieldtype": "Link", "options": "Fixed Asset Disposal", "width": 150},
		{"label": _("Disposal Date"), "fieldname": "disposal_date", "fieldtype": "Date", "width": 120},
		{"label": _("Asset"), "fieldname": "fixed_asset", "fieldtype": "Link", "options": "Fixed Asset", "width": 150},
		{"label": _("Carrying Amount"), "fieldname": "carrying_amount_snapshot", "fieldtype": "Currency", "width": 140},
		{"label": _("Proceeds"), "fieldname": "proceeds", "fieldtype": "Currency", "width": 130},
		{"label": _("Gain / Loss"), "fieldname": "gain_or_loss", "fieldtype": "Currency", "width": 130},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart