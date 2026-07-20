import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conditions = ["fa.company=%(company)s"]
	if filters.get("branch"):
		conditions.append("fa.branch=%(branch)s")

	data = frappe.db.sql(
		f"""
		select
			fa.name,
			fa.asset_name,
			fa.company,
			fa.branch,
			fa.criticality,
			coalesce(fa.risk_score, 0) as risk_score,
			coalesce(fa.health_score, 0) as health_score,
			coalesce(fa.capital_risk, 0) as capital_risk,
			coalesce(fa.maintenance_burden, 0) as maintenance_burden,
			fa.replacement_recommendation
		from `tabFixed Asset` fa
		where {' and '.join(conditions)}
		order by coalesce(fa.risk_score, 0) desc, fa.asset_name
		""",
		filters,
		as_dict=True,
	)
	columns = [
		{"label": _("Asset"), "fieldname": "name", "fieldtype": "Link", "options": "Fixed Asset", "width": 150
	},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180
	},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120
	},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120
	},
		{"label": _("Criticality"), "fieldname": "criticality", "fieldtype": "Data", "width": 110
	},
		{"label": _("Risk Score"), "fieldname": "risk_score", "fieldtype": "Percent", "width": 95
	},
		{"label": _("Health Score"), "fieldname": "health_score", "fieldtype": "Percent", "width": 95
	},
		{"label": _("Capital Risk"), "fieldname": "capital_risk", "fieldtype": "Percent", "width": 100
	},
		{"label": _("Maintenance Burden"), "fieldname": "maintenance_burden", "fieldtype": "Percent", "width": 130
	},
		{"label": _("Replacement Recommendation"), "fieldname": "replacement_recommendation", "fieldtype": "Small Text", "width": 260
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart