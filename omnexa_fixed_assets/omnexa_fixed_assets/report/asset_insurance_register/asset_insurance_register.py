# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	conditions = ["ip.company = %(company)s", "ip.docstatus < 2"]
	params = {"company": filters.company
	}

	if filters.get("insurance_company"):
		conditions.append("ip.insurance_company = %(insurance_company)s")
		params["insurance_company"] = filters.insurance_company

	if filters.get("policy_status"):
		conditions.append("ip.policy_status = %(policy_status)s")
		params["policy_status"] = filters.policy_status

	data = frappe.db.sql(
		f"""
		SELECT
			ip.name AS insurance_policy,
			ip.policy_status,
			ip.insurance_company,
			ip.coverage_type,
			ip.fixed_asset,
			fa.asset_name,
			fa.branch AS asset_branch,
			ip.start_date,
			ip.end_date,
			ip.annual_premium,
			ip.docstatus
		FROM `tabInsurance Policy` ip
		LEFT JOIN `tabFixed Asset` fa ON fa.name = ip.fixed_asset
		WHERE {' AND '.join(conditions)}
		ORDER BY ip.modified DESC
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("Insurance Policy"), "fieldname": "insurance_policy", "fieldtype": "Link", "options": "Insurance Policy", "width": 160
	},
		{"label": _("Status"), "fieldname": "policy_status", "fieldtype": "Data", "width": 110
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
		{"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Date", "width": 110
	},
		{"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Date", "width": 110
	},
		{"label": _("Annual Premium"), "fieldname": "annual_premium", "fieldtype": "Currency", "width": 130
	},
		{"label": _("Docstatus"), "fieldname": "docstatus", "fieldtype": "Int", "width": 80
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart