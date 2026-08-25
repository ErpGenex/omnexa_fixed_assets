# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Hotel asset register — IAS 16 cost model assets linked to hotel properties."""

from __future__ import annotations

import frappe
from frappe import _

from omnexa_core.omnexa_core.branch_access import get_allowed_branches
from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled
from omnexa_fixed_assets.utils.report_filters import merge_navbar_report_filters


def execute(filters=None):
	enforce_hotel_feature_enabled()
	filters = merge_navbar_report_filters(filters)
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	params = {"company": filters.company}
	conditions = [
		"fa.company = %(company)s",
		"IFNULL(fa.hotel_property, '') != ''",
	]
	if filters.get("branch"):
		params["branch"] = filters.branch
		conditions.append("fa.branch = %(branch)s")
	if filters.get("hotel_property"):
		params["hotel_property"] = filters.hotel_property
		conditions.append("fa.hotel_property = %(hotel_property)s")
	if filters.get("status"):
		params["status"] = filters.status
		conditions.append("fa.status = %(status)s")

	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return _columns(), []
		params["allowed_branches"] = tuple(allowed)
		conditions.append("fa.branch IN %(allowed_branches)s")

	data = frappe.db.sql(
		f"""
		SELECT
			fa.name,
			fa.asset_name,
			fa.hotel_property,
			fa.hotel_room,
			fa.hotel_functional_area,
			fa.category,
			fa.status,
			fa.capitalization_date AS acquisition_date,
			fa.acquisition_cost,
			fa.accumulated_depreciation,
			fa.net_book_value,
			fa.branch,
			fa.rfid_tag
		FROM `tabFixed Asset` fa
		WHERE {" AND ".join(conditions)}
		ORDER BY fa.hotel_property, fa.hotel_room, fa.asset_name
		""",
		params,
		as_dict=True,
	)
	columns = _columns()
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart


def _columns():
	return [
		{"label": _("Asset"), "fieldname": "name", "fieldtype": "Link", "options": "Fixed Asset", "width": 130},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180},
		{"label": _("Hotel Property"), "fieldname": "hotel_property", "fieldtype": "Link", "options": "Hotel Property", "width": 170},
		{"label": _("Room"), "fieldname": "hotel_room", "fieldtype": "Link", "options": "Hotel Room", "width": 130},
		{"label": _("Functional Area"), "fieldname": "hotel_functional_area", "fieldtype": "Link", "options": "Hotel Functional Area", "width": 150},
		{"label": _("Category"), "fieldname": "category", "fieldtype": "Link", "options": "Fixed Asset Category", "width": 130},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Acquisition Date"), "fieldname": "acquisition_date", "fieldtype": "Date", "width": 110},
		{"label": _("Cost"), "fieldname": "acquisition_cost", "fieldtype": "Currency", "width": 120},
		{"label": _("Accum. Depreciation"), "fieldname": "accumulated_depreciation", "fieldtype": "Currency", "width": 130},
		{"label": _("NBV"), "fieldname": "net_book_value", "fieldtype": "Currency", "width": 120},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 110},
		{"label": _("RFID"), "fieldname": "rfid_tag", "fieldtype": "Data", "width": 120},
	]
