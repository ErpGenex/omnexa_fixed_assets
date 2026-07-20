# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import getdate

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled


def execute(filters=None):
	enforce_hotel_feature_enabled()
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	params = {
		"company": filters.company,
		"from_date": getdate(filters.from_date),
		"to_date": getdate(filters.to_date),
	}
	conditions = [
		"de.company = %(company)s",
		"de.posting_date BETWEEN %(from_date)s AND %(to_date)s",
		"de.docstatus = 1",
		"IFNULL(fa.hotel_property, '') != ''",
	]
	if filters.get("hotel_property"):
		params["hotel_property"] = filters.hotel_property
		conditions.append("fa.hotel_property = %(hotel_property)s")

	data = frappe.db.sql(
		f"""
		SELECT
			de.posting_date,
			fa.hotel_property,
			fa.hotel_room,
			de.fixed_asset,
			fa.asset_name,
			SUM(de.depreciation_amount) AS depreciation_amount
		FROM `tabFixed Asset Depreciation Entry` de
		INNER JOIN `tabFixed Asset` fa ON fa.name = de.fixed_asset
		WHERE {' AND '.join(conditions)}
		GROUP BY de.posting_date, fa.hotel_property, fa.hotel_room, de.fixed_asset, fa.asset_name
		ORDER BY de.posting_date DESC, fa.hotel_property, fa.hotel_room, fa.asset_name
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": _("Hotel Property"), "fieldname": "hotel_property", "fieldtype": "Link", "options": "Hotel Property", "width": 180},
		{"label": _("Hotel Room"), "fieldname": "hotel_room", "fieldtype": "Link", "options": "Hotel Room", "width": 150},
		{"label": _("Fixed Asset"), "fieldname": "fixed_asset", "fieldtype": "Link", "options": "Fixed Asset", "width": 160},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 200},
		{"label": _("Depreciation"), "fieldname": "depreciation_amount", "fieldtype": "Currency", "width": 140},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart