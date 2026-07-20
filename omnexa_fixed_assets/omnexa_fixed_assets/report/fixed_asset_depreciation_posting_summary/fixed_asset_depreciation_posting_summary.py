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

	conditions = ["fa.company = %(company)s", "fa.docstatus = 1"]
	if filters.get("branch"):
		conditions.append("fa.branch = %(branch)s")
	if filters.get("from_date"):
		conditions.append("fa.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("fa.posting_date <= %(to_date)s")

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
			DATE_FORMAT(fa.posting_date, '%%Y-%%m') AS period,
			COUNT(*) AS posting_count,
			COALESCE(SUM(fa.depreciation_amount), 0) AS depreciation_amount
		FROM `tabFixed Asset Depreciation Entry` fa
		WHERE {' AND '.join(conditions)}
		GROUP BY fa.branch, DATE_FORMAT(fa.posting_date, '%%Y-%%m')
		ORDER BY period DESC, fa.branch
		""",
		filters,
		as_dict=True,
	)

	for row in data:
		row["depreciation_amount"] = flt(row.depreciation_amount)
	columns = _columns()
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart


def _columns():
	return [
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 130
	},
		{"label": _("Period (YYYY-MM)"), "fieldname": "period", "fieldtype": "Data", "width": 120
	},
		{"label": _("Postings"), "fieldname": "posting_count", "fieldtype": "Int", "width": 90
	},
		{"label": _("Depreciation Amount"), "fieldname": "depreciation_amount", "fieldtype": "Currency", "width": 160
	},
	]
