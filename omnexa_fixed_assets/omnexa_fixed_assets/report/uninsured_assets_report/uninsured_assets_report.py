# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	today = getdate()
	params = {"company": filters.company, "today": today
	}
	extra = ""
	if filters.get("fixed_asset_category"):
		params["category"] = filters.fixed_asset_category
		extra = " AND fa.category = %(category)s"

	data = frappe.db.sql(
		f"""
		SELECT
			fa.name AS fixed_asset,
			fa.asset_name,
			fa.category,
			fa.status
		FROM `tabFixed Asset` fa
		WHERE fa.company = %(company)s
			AND fa.docstatus < 2
			AND IFNULL(fa.status, '') NOT IN ('disposed', 'draft')
			{extra}
			AND NOT EXISTS (
				SELECT 1 FROM `tabInsurance Policy` ip
				WHERE ip.fixed_asset = fa.name
					AND ip.company = %(company)s
					AND ip.docstatus = 1
					AND ip.policy_status = 'Active'
					AND (ip.end_date IS NULL OR ip.end_date >= %(today)s)
			)
		ORDER BY fa.asset_name
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("Fixed Asset"), "fieldname": "fixed_asset", "fieldtype": "Link", "options": "Fixed Asset", "width": 160
	},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 200
	},
		{"label": _("Category"), "fieldname": "category", "fieldtype": "Link", "options": "Fixed Asset Category", "width": 160
	},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart