import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from omnexa_fixed_assets.utils.report_filters import merge_navbar_report_filters


def execute(filters=None):
	filters = merge_navbar_report_filters(filters)
	conditions = ["rt.company=%(company)s"]
	if filters.get("branch"):
		conditions.append("rt.branch=%(branch)s")
	if filters.get("from_date"):
		conditions.append("rt.as_of_date>=%(from_date)s")
	if filters.get("to_date"):
		conditions.append("rt.as_of_date<=%(to_date)s")

	data = frappe.db.sql(
		f"""
		select
			rt.asset,
			fa.asset_name,
			rt.company,
			rt.branch,
			rt.as_of_date,
			coalesce(rt.mtbf, 0) as mtbf,
			coalesce(rt.mttr, 0) as mttr,
			coalesce(rt.availability, 0) as availability,
			coalesce(rt.failure_frequency, 0) as failure_frequency,
			coalesce(rt.reliability_score, 0) as reliability_score
		from `tabAsset Reliability Trend` rt
		left join `tabFixed Asset` fa on fa.name = rt.asset
		where {' and '.join(conditions)}
		order by rt.as_of_date desc, rt.asset
		""",
		filters,
		as_dict=True,
	)
	columns = [
		{"label": _("Asset"), "fieldname": "asset", "fieldtype": "Link", "options": "Fixed Asset", "width": 150
	},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180
	},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120
	},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120
	},
		{"label": _("As Of"), "fieldname": "as_of_date", "fieldtype": "Date", "width": 100
	},
		{"label": _("MTBF (h)"), "fieldname": "mtbf", "fieldtype": "Float", "width": 95
	},
		{"label": _("MTTR (h)"), "fieldname": "mttr", "fieldtype": "Float", "width": 95
	},
		{"label": _("Availability %"), "fieldname": "availability", "fieldtype": "Percent", "width": 110
	},
		{"label": _("Failure Freq"), "fieldname": "failure_frequency", "fieldtype": "Float", "width": 100
	},
		{"label": _("Reliability %"), "fieldname": "reliability_score", "fieldtype": "Percent", "width": 110
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart