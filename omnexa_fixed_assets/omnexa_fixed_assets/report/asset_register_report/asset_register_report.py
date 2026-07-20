# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	params = {"company": filters.company
	}
	conditions = ["fa.company = %(company)s"]
	if filters.get("branch"):
		params["branch"] = filters.branch
		conditions.append("fa.branch = %(branch)s")
	if filters.get("status"):
		params["status"] = filters.status
		conditions.append("fa.status = %(status)s")

	data = frappe.db.sql(
		f"""
		SELECT
			fa.name,
			fa.asset_name,
			fa.category,
			fa.status,
			fa.acquisition_cost,
			fa.accumulated_depreciation,
			fa.net_book_value,
			fa.company,
			fa.branch
		FROM `tabFixed Asset` fa
		WHERE {' AND '.join(conditions)}
		ORDER BY fa.modified DESC
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("Asset"), "fieldname": "name", "fieldtype": "Link", "options": "Fixed Asset", "width": 150
	},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180
	},
		{"label": _("Category"), "fieldname": "category", "fieldtype": "Link", "options": "Fixed Asset Category", "width": 150
	},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 130
	},
		{"label": _("Acquisition Cost"), "fieldname": "acquisition_cost", "fieldtype": "Currency", "width": 130
	},
		{"label": _("Accum. Depreciation"), "fieldname": "accumulated_depreciation", "fieldtype": "Currency", "width": 140
	},
		{"label": _("Net Book Value"), "fieldname": "net_book_value", "fieldtype": "Currency", "width": 130
	},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120
	},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart