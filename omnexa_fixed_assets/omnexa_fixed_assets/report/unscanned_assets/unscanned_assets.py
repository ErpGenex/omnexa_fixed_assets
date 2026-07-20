# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import cint, getdate, today

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled


def execute(filters=None):
	enforce_hotel_feature_enabled()
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	as_of = getdate(filters.get("as_of") or today())
	min_gap = max(0, cint(filters.get("min_gap_days") or 7))
	include_never = cint(filters.get("include_never_scanned") or 0) == 1

	params = {"company": filters.company, "as_of": as_of, "min_gap": min_gap}
	where = [
		"fa.company = %(company)s",
		"fa.docstatus < 2",
		"IFNULL(fa.rfid_tag, '') != ''",
	]

	having = ["DATEDIFF(%(as_of)s, MAX(r.scan_time)) > %(min_gap)s"]
	if include_never:
		having.insert(0, "MAX(r.scan_time) IS NULL")
	having_sql = " OR ".join([f"({x})" for x in having])

	data = frappe.db.sql(
		f"""
		SELECT
			fa.name AS fixed_asset,
			fa.asset_name,
			fa.hotel_property,
			fa.hotel_room,
			fa.rfid_tag,
			MAX(r.scan_time) AS last_scan_time,
			DATEDIFF(%(as_of)s, MAX(r.scan_time)) AS days_since_scan
		FROM `tabFixed Asset` fa
		LEFT JOIN `tabRFID Scan Log` r
			ON r.fixed_asset = fa.name AND r.docstatus < 2
		WHERE {' AND '.join(where)}
		GROUP BY fa.name, fa.asset_name, fa.hotel_property, fa.hotel_room, fa.rfid_tag
		HAVING {having_sql}
		ORDER BY last_scan_time IS NULL DESC, days_since_scan DESC, fa.hotel_property, fa.hotel_room, fa.asset_name
		""",
		params,
		as_dict=True,
	)

	columns = [
		{"label": _("Fixed Asset"), "fieldname": "fixed_asset", "fieldtype": "Link", "options": "Fixed Asset", "width": 160},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180},
		{"label": _("Hotel Property"), "fieldname": "hotel_property", "fieldtype": "Link", "options": "Hotel Property", "width": 180},
		{"label": _("Hotel Room"), "fieldname": "hotel_room", "fieldtype": "Link", "options": "Hotel Room", "width": 150},
		{"label": _("RFID Tag"), "fieldname": "rfid_tag", "fieldtype": "Data", "width": 140},
		{"label": _("Last Scan"), "fieldname": "last_scan_time", "fieldtype": "Datetime", "width": 170},
		{"label": _("Days Since"), "fieldname": "days_since_scan", "fieldtype": "Int", "width": 110},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart