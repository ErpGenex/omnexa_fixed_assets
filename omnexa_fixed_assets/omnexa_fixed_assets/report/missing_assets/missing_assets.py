# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns

from omnexa_core.omnexa_core.report_print.report_query_filters import (
	get_all_filters,
	policy_version_filters,
	prepare_filters,
	sql_conditions,
)



def execute(filters=None):
	from omnexa_fixed_assets.utils.report_filters import merge_navbar_report_filters

	filters = merge_navbar_report_filters(prepare_filters(filters))
	filters_dict = get_all_filters(filters, "Fixed Asset", date_field="creation", company=True, branch=True, extra_links={})
	filters_dict["scan_status"] = ["in", ["Missing", "Mismatch"]]
	data = frappe.get_all(
		"Fixed Asset",
		fields=['name', 'asset_name', 'hotel_property', 'hotel_room', 'scan_status', 'modified'],
		filters=filters_dict,
		limit_page_length=5000,
	)

	return [
		{"label": _("Asset"), "fieldname": "name", "fieldtype": "Link", "options": "Fixed Asset", "width": 150
	},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180
	},
		{"label": _("Hotel Property"), "fieldname": "hotel_property", "fieldtype": "Link", "options": "Hotel Property", "width": 200
	},
		{"label": _("Hotel Room"), "fieldname": "hotel_room", "fieldtype": "Link", "options": "Hotel Room", "width": 170
	},
		{"label": _("Scan Status"), "fieldname": "scan_status", "fieldtype": "Data", "width": 120
	},
		{"label": _("Last Update"), "fieldname": "modified", "fieldtype": "Datetime", "width": 170
	},
	], data
