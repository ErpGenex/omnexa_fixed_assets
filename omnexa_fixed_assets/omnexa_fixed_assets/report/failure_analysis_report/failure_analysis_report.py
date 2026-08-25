import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from omnexa_fixed_assets.utils.report_filters import merge_navbar_report_filters


def execute(filters=None):
	filters = merge_navbar_report_filters(filters)
	conditions = ["fe.company=%(company)s"]
	if filters.get("branch"):
		conditions.append("fe.branch=%(branch)s")
	if filters.get("from_date"):
		conditions.append("date(fe.event_time)>=%(from_date)s")
	if filters.get("to_date"):
		conditions.append("date(fe.event_time)<=%(to_date)s")

	data = frappe.db.sql(
		f"""
		select
			fe.asset,
			fa.asset_name,
			coalesce(fe.category, 'Uncategorized') as category,
			coalesce(fe.cause, '') as cause,
			count(*) as failure_count,
			coalesce(sum(fe.downtime_hours), 0) as total_downtime_hours
		from `tabAsset Failure Event` fe
		left join `tabFixed Asset` fa on fa.name = fe.asset
		where {' and '.join(conditions)}
		group by fe.asset, coalesce(fe.category, 'Uncategorized'), coalesce(fe.cause, '')
		order by failure_count desc, total_downtime_hours desc
		""",
		filters,
		as_dict=True,
	)
	columns = [
		{"label": _("Asset"), "fieldname": "asset", "fieldtype": "Link", "options": "Fixed Asset", "width": 150
	},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180
	},
		{"label": _("Category"), "fieldname": "category", "fieldtype": "Data", "width": 140
	},
		{"label": _("Cause"), "fieldname": "cause", "fieldtype": "Data", "width": 200
	},
		{"label": _("Failure Count"), "fieldname": "failure_count", "fieldtype": "Int", "width": 110
	},
		{"label": _("Downtime (h)"), "fieldname": "total_downtime_hours", "fieldtype": "Float", "width": 110
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart