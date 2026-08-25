import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from omnexa_fixed_assets.utils.report_filters import merge_navbar_report_filters


def execute(filters=None):
	filters = merge_navbar_report_filters(filters)
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
			fa.inspection_due,
			max(ai.inspection_date) as last_inspection_date,
			case
				when fa.inspection_due is null then 'No Schedule'
				when fa.inspection_due >= curdate() then 'Compliant'
				else 'Overdue'
			end as compliance_status
		from `tabFixed Asset` fa
		left join `tabAsset Inspection` ai on ai.asset = fa.name and ai.docstatus < 2
		where {' and '.join(conditions)}
		group by fa.name, fa.asset_name, fa.company, fa.branch, fa.inspection_due
		order by case when fa.inspection_due is null then 2 when fa.inspection_due < curdate() then 0 else 1 end, fa.inspection_due asc
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
		{"label": _("Inspection Due"), "fieldname": "inspection_due", "fieldtype": "Date", "width": 120
	},
		{"label": _("Last Inspection"), "fieldname": "last_inspection_date", "fieldtype": "Datetime", "width": 150
	},
		{"label": _("Compliance"), "fieldname": "compliance_status", "fieldtype": "Data", "width": 120
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart