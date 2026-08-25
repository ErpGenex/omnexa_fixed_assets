# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import getdate

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled
from omnexa_fixed_assets.utils.report_filters import merge_navbar_report_filters


def execute(filters=None):
	enforce_hotel_feature_enabled()
	filters = merge_navbar_report_filters(filters)
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	params = {
		"company": filters.company,
		"from_date": getdate(filters.from_date),
		"to_date": getdate(filters.to_date)
	}
	conditions = [
		"hi.company = %(company)s",
		"hi.inspection_date BETWEEN %(from_date)s AND %(to_date)s",
		"hi.docstatus < 2",
	]
	if filters.get("hotel_property"):
		params["hotel_property"] = filters.hotel_property
		conditions.append("hi.hotel_property = %(hotel_property)s")

	data = frappe.db.sql(
		f"""
		SELECT
			IFNULL(hi.hotel_property, '') AS hotel_property,
			hi.inspection_result_action,
			hi.condition_status,
			COUNT(*) AS inspection_count,
			MAX(hi.inspection_date) AS last_inspection_date
		FROM `tabHotel Asset Inspection` hi
		WHERE {' AND '.join(conditions)}
		GROUP BY hi.hotel_property, hi.inspection_result_action, hi.condition_status
		ORDER BY hotel_property, inspection_result_action, condition_status
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("Hotel Property"), "fieldname": "hotel_property", "fieldtype": "Link", "options": "Hotel Property", "width": 200
	},
		{"label": _("Result Action"), "fieldname": "inspection_result_action", "fieldtype": "Data", "width": 120
	},
		{"label": _("Condition"), "fieldname": "condition_status", "fieldtype": "Data", "width": 110
	},
		{"label": _("Inspections"), "fieldname": "inspection_count", "fieldtype": "Int", "width": 110
	},
		{"label": _("Last Inspection"), "fieldname": "last_inspection_date", "fieldtype": "Date", "width": 130
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart