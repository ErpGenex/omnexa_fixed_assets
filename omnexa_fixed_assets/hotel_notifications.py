# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Scheduled hotel asset notifications (warranty, etc.)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, formatdate, getdate, now_datetime

from omnexa_fixed_assets.utils.feature_flags import site_has_any_hotel_assets_company


def create_warranty_expiry_alerts(lookahead_days: int = 30) -> int:
	"""Create open Asset Alert rows for hotel-linked assets whose warranty ends within the window.

	Idempotent: skips if an open Warranty Warning already exists for the asset.
	Returns count of newly created alerts.
	"""
	if not site_has_any_hotel_assets_company():
		return 0
	if not frappe.db.exists("DocType", "Asset Alert"):
		return 0
	for col in ("hotel_property", "warranty_end_date"):
		if not frappe.db.has_column("Fixed Asset", col):
			return 0

	today = getdate()
	end = add_days(today, lookahead_days)
	assets = frappe.db.sql(
		"""
		SELECT name, company, branch, asset_name, warranty_end_date
		FROM `tabFixed Asset`
		WHERE docstatus < 2
			AND IFNULL(hotel_property, '') != ''
			AND warranty_end_date IS NOT NULL
			AND warranty_end_date BETWEEN %s AND %s
		""",
		(today, end),
		as_dict=True,
	)

	created = 0
	for a in assets:
		if frappe.db.exists(
			"Asset Alert",
			{"asset": a.name, "alert_type": "Warranty Warning", "status": "Open"
	},
		):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Asset Alert",
				"asset": a.name,
				"company": a.company,
				"branch": a.branch,
				"alert_time": now_datetime(),
				"alert_type": "Warranty Warning",
				"severity": "Medium",
				"status": "Open",
				"message": _("Hotel asset warranty expires on {0} ({1})").format(
					formatdate(a.warranty_end_date),
					a.asset_name or a.name,
				),
				"source": "Hotel Asset Scheduler"
	}
		)
		doc.insert(ignore_permissions=True)
		created += 1

	return created
