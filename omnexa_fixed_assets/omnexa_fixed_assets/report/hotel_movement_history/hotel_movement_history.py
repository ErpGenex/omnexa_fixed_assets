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

	params: dict = {"company": filters.company}
	conditions = ["t.company = %(company)s", "t.docstatus < 2"]

	if filters.get("fixed_asset"):
		params["fixed_asset"] = filters.fixed_asset
		conditions.append("t.fixed_asset = %(fixed_asset)s")
	if filters.get("from_date"):
		params["from_date"] = getdate(filters.from_date)
		conditions.append("t.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		params["to_date"] = getdate(filters.to_date)
		conditions.append("t.posting_date <= %(to_date)s")

	data = frappe.db.sql(
		f"""
		SELECT
			t.name AS transfer,
			t.posting_date,
			t.fixed_asset,
			t.approval_status,
			t.from_hotel_property,
			t.from_hotel_room,
			t.to_hotel_property,
			t.to_hotel_room,
			t.notes
		FROM `tabHotel Asset Transfer` t
		WHERE {' AND '.join(conditions)}
		ORDER BY t.posting_date DESC, t.modified DESC
		""",
		params,
		as_dict=True,
	)

	columns = [
		{"label": _("Transfer"), "fieldname": "transfer", "fieldtype": "Link", "options": "Hotel Asset Transfer", "width": 160},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": _("Fixed Asset"), "fieldname": "fixed_asset", "fieldtype": "Link", "options": "Fixed Asset", "width": 160},
		{"label": _("Approval"), "fieldname": "approval_status", "fieldtype": "Data", "width": 110},
		{"label": _("From Property"), "fieldname": "from_hotel_property", "fieldtype": "Link", "options": "Hotel Property", "width": 170},
		{"label": _("From Room"), "fieldname": "from_hotel_room", "fieldtype": "Link", "options": "Hotel Room", "width": 160},
		{"label": _("To Property"), "fieldname": "to_hotel_property", "fieldtype": "Link", "options": "Hotel Property", "width": 170},
		{"label": _("To Room"), "fieldname": "to_hotel_room", "fieldtype": "Link", "options": "Hotel Room", "width": 160},
		{"label": _("Notes"), "fieldname": "notes", "fieldtype": "Small Text", "width": 220},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart