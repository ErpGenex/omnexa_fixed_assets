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
	conditions = ["fa.company = %(company)s"]
	if filters.get("hotel_property"):
		params["hotel_property"] = filters.hotel_property
		conditions.append("fa.hotel_property = %(hotel_property)s")

	data = frappe.db.sql(
		f"""
		SELECT
			fa.hotel_property,
			fa.hotel_room,
			COUNT(*) AS asset_count
		FROM `tabFixed Asset` fa
		WHERE {' AND '.join(conditions)}
		GROUP BY fa.hotel_property, fa.hotel_room
		ORDER BY fa.hotel_property, fa.hotel_room
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("Hotel Property"), "fieldname": "hotel_property", "fieldtype": "Link", "options": "Hotel Property", "width": 220
	},
		{"label": _("Hotel Room"), "fieldname": "hotel_room", "fieldtype": "Link", "options": "Hotel Room", "width": 200
	},
		{"label": _("Assets"), "fieldname": "asset_count", "fieldtype": "Int", "width": 110
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart