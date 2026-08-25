# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.report_print.report_query_filters import get_all_filters, prepare_filters


def execute(filters=None):
	from omnexa_fixed_assets.utils.report_filters import merge_navbar_report_filters

	filters = merge_navbar_report_filters(prepare_filters(filters))
	filters_dict = get_all_filters(filters, "Linen Item", date_field="modified", company=True, branch=True, extra_links={})
	filters_dict["status"] = ["in", ["Missing", "Disposed"]]
	data = frappe.get_all(
		"Linen Item",
		fields=[
			"name",
			"linen_name",
			"linen_type",
			"status",
			"hotel_property",
			"current_location",
			"last_seen_at",
			"rfid_tag",
		],
		filters=filters_dict,
		limit_page_length=5000,
	)
	shortages = frappe.get_all(
		"Linen Shortage Alert",
		filters={"company": filters_dict.get("company"), "status": "Open"},
		fields=["name", "linen_type", "missing_quantity", "message", "alert_time", "hotel_property"],
		limit_page_length=500,
	)
	for row in shortages:
		data.append(
			{
				"name": row.name,
				"linen_name": row.message,
				"linen_type": row.linen_type,
				"status": "Shortage Alert",
				"hotel_property": row.hotel_property,
				"current_location": None,
				"last_seen_at": row.alert_time,
				"rfid_tag": None,
			}
		)
	return [
		{"label": _("Linen Item"), "fieldname": "name", "fieldtype": "Data", "width": 140},
		{"label": _("Name"), "fieldname": "linen_name", "fieldtype": "Data", "width": 200},
		{"label": _("Type"), "fieldname": "linen_type", "fieldtype": "Data", "width": 120},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": _("Property"), "fieldname": "hotel_property", "fieldtype": "Link", "options": "Hotel Property", "width": 160},
		{"label": _("Last Location"), "fieldname": "current_location", "fieldtype": "Data", "width": 160},
		{"label": _("Last Seen"), "fieldname": "last_seen_at", "fieldtype": "Datetime", "width": 160},
		{"label": _("RFID Tag"), "fieldname": "rfid_tag", "fieldtype": "Data", "width": 140},
	], data
