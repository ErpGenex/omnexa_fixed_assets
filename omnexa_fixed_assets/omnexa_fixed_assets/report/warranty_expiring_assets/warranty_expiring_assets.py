# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import add_days, cint, getdate

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled
from omnexa_fixed_assets.utils.report_filters import merge_navbar_report_filters


def execute(filters=None):
	enforce_hotel_feature_enabled()
	filters = merge_navbar_report_filters(filters)
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	days_ahead = cint(filters.get("days_ahead") or 90)
	if days_ahead < 0:
		frappe.throw(_("Days ahead cannot be negative."), title=_("Filters"))

	today = getdate()
	params = {
		"company": filters.company,
		"today": today,
		"end": add_days(today, days_ahead)}
	conditions = [
		"fa.company = %(company)s",
		"fa.docstatus < 2",
		"fa.warranty_end_date IS NOT NULL",
		"fa.warranty_end_date >= %(today)s",
		"fa.warranty_end_date <= %(end)s",
		"IFNULL(fa.hotel_property, '') != ''",
	]
	if filters.get("hotel_property"):
		params["hotel_property"] = filters.hotel_property
		conditions.append("fa.hotel_property = %(hotel_property)s")

	data = frappe.db.sql(
		f"""
		SELECT
			fa.name AS fixed_asset,
			fa.asset_name,
			fa.hotel_property,
			fa.hotel_room,
			fa.warranty_supplier,
			fa.warranty_end_date,
			DATEDIFF(fa.warranty_end_date, %(today)s) AS days_remaining
		FROM `tabFixed Asset` fa
		WHERE {' AND '.join(conditions)}
		ORDER BY fa.warranty_end_date ASC, fa.hotel_property, fa.asset_name
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("Fixed Asset"), "fieldname": "fixed_asset", "fieldtype": "Link", "options": "Fixed Asset", "width": 160
	},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 200
	},
		{"label": _("Hotel Property"), "fieldname": "hotel_property", "fieldtype": "Link", "options": "Hotel Property", "width": 180
	},
		{"label": _("Hotel Room"), "fieldname": "hotel_room", "fieldtype": "Link", "options": "Hotel Room", "width": 150
	},
		{"label": _("Warranty Supplier"), "fieldname": "warranty_supplier", "fieldtype": "Link", "options": "Supplier", "width": 170
	},
		{"label": _("Warranty End Date"), "fieldname": "warranty_end_date", "fieldtype": "Date", "width": 130
	},
		{"label": _("Days Remaining"), "fieldname": "days_remaining", "fieldtype": "Int", "width": 120
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart