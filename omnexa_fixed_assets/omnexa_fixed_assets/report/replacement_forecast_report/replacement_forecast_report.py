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
			fa.criticality,
			coalesce(fa.health_status, 'Unknown') as health_status,
			coalesce(fa.health_score, 0) as health_score,
			coalesce(fa.risk_score, 0) as risk_score,
			coalesce(fa.replacement_projection, 0) as replacement_projection,
			coalesce(fa.net_book_value, 0) as net_book_value,
			coalesce(fa.replacement_recommendation, '') as replacement_recommendation
		from `tabFixed Asset` fa
		where {' and '.join(conditions)}
		order by coalesce(fa.risk_score, 0) desc, coalesce(fa.replacement_projection, 0) desc
		""",
		filters,
		as_dict=True,
	)
	columns = [
		{"label": _("Asset"), "fieldname": "name", "fieldtype": "Link", "options": "Fixed Asset", "width": 150
	},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180
	},
		{"label": _("Criticality"), "fieldname": "criticality", "fieldtype": "Data", "width": 110
	},
		{"label": _("Health Status"), "fieldname": "health_status", "fieldtype": "Data", "width": 110
	},
		{"label": _("Health Score"), "fieldname": "health_score", "fieldtype": "Percent", "width": 95
	},
		{"label": _("Risk Score"), "fieldname": "risk_score", "fieldtype": "Percent", "width": 95
	},
		{"label": _("Replacement Projection"), "fieldname": "replacement_projection", "fieldtype": "Currency", "width": 145
	},
		{"label": _("Net Book Value"), "fieldname": "net_book_value", "fieldtype": "Currency", "width": 130
	},
		{"label": _("Recommendation"), "fieldname": "replacement_recommendation", "fieldtype": "Small Text", "width": 240
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart