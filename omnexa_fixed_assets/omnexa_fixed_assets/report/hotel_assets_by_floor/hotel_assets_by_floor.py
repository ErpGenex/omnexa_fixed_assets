# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled
from omnexa_fixed_assets.utils.report_filters import merge_navbar_report_filters


def execute(filters=None):
	enforce_hotel_feature_enabled()
	filters = merge_navbar_report_filters(filters)
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	params = {"company": filters.company
	}
	conditions = ["fa.company = %(company)s", "IFNULL(fa.hotel_property, '') != ''"]
	if filters.get("hotel_property"):
		params["hotel_property"] = filters.hotel_property
		conditions.append("fa.hotel_property = %(hotel_property)s")

	data = frappe.db.sql(
		f"""
		SELECT
			fa.hotel_property,
			IFNULL(hr.floor, '') AS floor,
			IFNULL(hr.wing, '') AS wing,
			COUNT(*) AS asset_count
		FROM `tabFixed Asset` fa
		LEFT JOIN `tabHotel Room` hr ON hr.name = fa.hotel_room
		WHERE {' AND '.join(conditions)}
		GROUP BY fa.hotel_property, hr.floor, hr.wing
		ORDER BY fa.hotel_property, floor, wing
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("Hotel Property"), "fieldname": "hotel_property", "fieldtype": "Link", "options": "Hotel Property", "width": 200
	},
		{"label": _("Floor"), "fieldname": "floor", "fieldtype": "Data", "width": 120
	},
		{"label": _("Wing / Zone"), "fieldname": "wing", "fieldtype": "Data", "width": 140
	},
		{"label": _("Assets"), "fieldname": "asset_count", "fieldtype": "Int", "width": 110
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart