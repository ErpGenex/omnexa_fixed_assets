# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	conditions = ["m.company = %(company)s"]
	if filters.get("from_date"):
		conditions.append("m.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("m.posting_date <= %(to_date)s")

	data = frappe.db.sql(
		f"""
		SELECT
			m.posting_date,
			m.fixed_asset,
			m.movement_type,
			m.from_location,
			m.to_location,
			m.reference_doctype,
			m.reference_name,
			m.branch
		FROM `tabFixed Asset Movement Log` m
		WHERE {' AND '.join(conditions)}
		ORDER BY m.posting_date DESC, m.modified DESC
		""",
		filters,
		as_dict=True,
	)
	columns = [
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": _("Asset"), "fieldname": "fixed_asset", "fieldtype": "Link", "options": "Fixed Asset", "width": 150},
		{"label": _("Movement Type"), "fieldname": "movement_type", "fieldtype": "Data", "width": 130},
		{"label": _("From Location"), "fieldname": "from_location", "fieldtype": "Link", "options": "Fixed Asset Location", "width": 130},
		{"label": _("To Location"), "fieldname": "to_location", "fieldtype": "Link", "options": "Fixed Asset Location", "width": 130},
		{"label": _("Reference DocType"), "fieldname": "reference_doctype", "fieldtype": "Data", "width": 130},
		{"label": _("Reference Name"), "fieldname": "reference_name", "fieldtype": "Data", "width": 150},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart