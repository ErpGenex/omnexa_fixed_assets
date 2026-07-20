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
	if filters.get("status"):
		conditions.append("m.status = %(status)s")

	data = frappe.db.sql(
		f"""
		SELECT
			m.name,
			m.posting_date,
			m.fixed_asset,
			m.maintenance_type,
			m.status,
			m.cost_amount,
			m.branch
		FROM `tabFixed Asset Maintenance` m
		WHERE {' AND '.join(conditions)}
		ORDER BY m.posting_date DESC, m.name DESC
		""",
		filters,
		as_dict=True,
	)
	columns = [
		{"label": _("Maintenance"), "fieldname": "name", "fieldtype": "Link", "options": "Fixed Asset Maintenance", "width": 150
	},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120
	},
		{"label": _("Asset"), "fieldname": "fixed_asset", "fieldtype": "Link", "options": "Fixed Asset", "width": 150
	},
		{"label": _("Type"), "fieldname": "maintenance_type", "fieldtype": "Data", "width": 120
	},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120
	},
		{"label": _("Cost"), "fieldname": "cost_amount", "fieldtype": "Currency", "width": 130
	},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart