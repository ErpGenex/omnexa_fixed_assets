import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from omnexa_fixed_assets.utils.report_filters import merge_navbar_report_filters


def execute(filters=None):
	filters = merge_navbar_report_filters(filters)
	conditions = ["fa.company=%(company)s"]
	if filters.get("branch"):
		conditions.append("fa.branch=%(branch)s")
	if filters.get("health_status"):
		conditions.append("fa.health_status=%(health_status)s")

	data = frappe.db.sql(
		f"""
		select
			fa.name,
			fa.asset_name,
			fa.company,
			fa.branch,
			fa.criticality,
			fa.health_status,
			coalesce(fa.health_score, 0) as health_score,
			coalesce(fa.risk_score, 0) as risk_score,
			coalesce(fa.reliability_score, 0) as reliability_score,
			fa.inspection_due
		from `tabFixed Asset` fa
		where {' and '.join(conditions)}
		order by coalesce(fa.risk_score, 0) desc, coalesce(fa.health_score, 0) asc, fa.asset_name
		""",
		filters,
		as_dict=True,
	)

	columns = [
		{"label": _("Asset"), "fieldname": "name", "fieldtype": "Link", "options": "Fixed Asset", "width": 160
	},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 200
	},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 130
	},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 130
	},
		{"label": _("Criticality"), "fieldname": "criticality", "fieldtype": "Data", "width": 120
	},
		{"label": _("Health Status"), "fieldname": "health_status", "fieldtype": "Data", "width": 120
	},
		{"label": _("Health Score"), "fieldname": "health_score", "fieldtype": "Percent", "width": 110
	},
		{"label": _("Risk Score"), "fieldname": "risk_score", "fieldtype": "Percent", "width": 100
	},
		{"label": _("Reliability Score"), "fieldname": "reliability_score", "fieldtype": "Percent", "width": 130
	},
		{"label": _("Inspection Due"), "fieldname": "inspection_due", "fieldtype": "Date", "width": 120
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart