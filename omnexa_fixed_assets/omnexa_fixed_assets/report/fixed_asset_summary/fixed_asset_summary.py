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
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 150
	},
		{"label": _("Asset Count"), "fieldname": "asset_count", "fieldtype": "Int", "width": 120
	},
		{"label": _("Acquisition Cost"), "fieldname": "acquisition_cost", "fieldtype": "Currency", "width": 150
	},
		{"label": _("Accum. Depreciation"), "fieldname": "accumulated_depreciation", "fieldtype": "Currency", "width": 150
	},
		{"label": _("Net Book Value"), "fieldname": "net_book_value", "fieldtype": "Currency", "width": 150
	},
	]
	filters = prepare_filters(filters)
	conditions, params = sql_conditions(filters, "Fixed Asset", date_field="creation", company=True, branch=True)
	rows = frappe.db.sql(
		f"""
		SELECT
			status,
			COUNT(*) AS asset_count,
			SUM(IFNULL(acquisition_cost, 0)) AS acquisition_cost,
			SUM(IFNULL(accumulated_depreciation, 0)) AS accumulated_depreciation,
			SUM(IFNULL(net_book_value, 0)) AS net_book_value
		FROM `tabFixed Asset`
		WHERE {' AND '.join(conditions)}
		GROUP BY status
		ORDER BY asset_count DESC
		""",
		params,
		as_dict=True,
	)
	chart = auto_chart_for_columns(rows, columns)
	return columns, rows, None, chart