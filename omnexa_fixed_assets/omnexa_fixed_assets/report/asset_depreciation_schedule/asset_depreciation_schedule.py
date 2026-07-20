# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns

from omnexa_core.omnexa_core.report_print.report_query_filters import (
	get_all_filters,
	policy_version_filters,
	prepare_filters,
	sql_conditions,
)



def execute(filters=None):
	columns = [
		{"label": _("Depreciation Entry"), "fieldname": "name", "fieldtype": "Link", "options": "Fixed Asset Depreciation Entry", "width": 170
	},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110
	},
		{"label": _("Asset"), "fieldname": "fixed_asset", "fieldtype": "Link", "options": "Fixed Asset", "width": 150
	},
		{"label": _("Depreciation Amount"), "fieldname": "depreciation_amount", "fieldtype": "Currency", "width": 150
	},
		{"label": _("Journal Entry"), "fieldname": "journal_entry", "fieldtype": "Link", "options": "Journal Entry", "width": 150
	},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120
	},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120
	},
	]
	filters = prepare_filters(filters)
	conditions, params = sql_conditions(filters, "Fixed Asset Depreciation Entry", date_field="creation", company=True, branch=True)
	conditions = ["docstatus = 1"] + conditions
	rows = frappe.db.sql(
		f"""
		SELECT
			d.name,
			d.posting_date,
			d.fixed_asset,
			d.depreciation_amount,
			d.journal_entry,
			d.company,
			d.branch
		FROM `tabFixed Asset Depreciation Entry`
		WHERE {' AND '.join(conditions)}
		GROUP BY 1
		ORDER BY d.posting_date, d.name
		""",
		params,
		as_dict=True,
	)
	chart = auto_chart_for_columns(rows, columns)
	return columns, rows, None, chart