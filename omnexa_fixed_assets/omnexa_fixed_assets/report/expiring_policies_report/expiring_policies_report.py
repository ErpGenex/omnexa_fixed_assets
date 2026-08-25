# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import add_days, cint, getdate
from omnexa_fixed_assets.utils.report_filters import merge_navbar_report_filters


def execute(filters=None):
	filters = merge_navbar_report_filters(filters)
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	days_ahead = cint(filters.get("days_ahead") or 90)
	if days_ahead < 0:
		frappe.throw(_("Days ahead cannot be negative."), title=_("Filters"))

	today = getdate()
	params = {
		"company": filters.company,
		"today": today,
		"end": add_days(today, days_ahead)}
	conditions = [
		"ip.company = %(company)s",
		"ip.docstatus = 1",
		"ip.end_date IS NOT NULL",
		"ip.end_date >= %(today)s",
		"ip.end_date <= %(end)s",
	]
	if filters.get("insurance_company"):
		params["insurance_company"] = filters.insurance_company
		conditions.append("ip.insurance_company = %(insurance_company)s")

	data = frappe.db.sql(
		f"""
		SELECT
			ip.name AS insurance_policy,
			ip.insurance_company,
			ip.coverage_type,
			ip.fixed_asset,
			fa.asset_name,
			fa.branch AS asset_branch,
			ip.end_date,
			DATEDIFF(ip.end_date, %(today)s) AS days_to_expiry
		FROM `tabInsurance Policy` ip
		LEFT JOIN `tabFixed Asset` fa ON fa.name = ip.fixed_asset
		WHERE {' AND '.join(conditions)}
		ORDER BY ip.end_date ASC, ip.name
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("Insurance Policy"), "fieldname": "insurance_policy", "fieldtype": "Link", "options": "Insurance Policy", "width": 160
	},
		{"label": _("Insurance Company"), "fieldname": "insurance_company", "fieldtype": "Link", "options": "Insurance Company", "width": 170
	},
		{"label": _("Coverage Type"), "fieldname": "coverage_type", "fieldtype": "Link", "options": "Insurance Coverage Type", "width": 160
	},
		{"label": _("Fixed Asset"), "fieldname": "fixed_asset", "fieldtype": "Link", "options": "Fixed Asset", "width": 160
	},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180
	},
		{"label": _("Branch"), "fieldname": "asset_branch", "fieldtype": "Link", "options": "Branch", "width": 120
	},
		{"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Date", "width": 120
	},
		{"label": _("Days to Expiry"), "fieldname": "days_to_expiry", "fieldtype": "Int", "width": 120
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart