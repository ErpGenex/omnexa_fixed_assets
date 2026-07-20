# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe
from frappe.utils import flt


def execute():
	"""Initialize additive EAM fields for existing Fixed Asset records."""
	if not frappe.db.exists("DocType", "Fixed Asset"):
		return
	if not frappe.db.has_column("Fixed Asset", "health_status"):
		return

	rows = frappe.get_all(
		"Fixed Asset",
		fields=[
			"name",
			"acquisition_cost",
			"net_book_value",
			"runtime_hours",
			"asset_path",
			"asset_level",
			"health_status",
		],
		limit_page_length=200000,
	)
	for row in rows:
		values = {}
		if not (row.asset_path or "").strip():
			values["asset_path"] = row.name
		if row.asset_level is None:
			values["asset_level"] = 0
		if not (row.health_status or "").strip():
			values["health_status"] = "Fair"
			values["health_score"] = 50.0
		if flt(row.acquisition_cost) and flt(row.net_book_value) >= 0:
			values["replacement_projection"] = max(flt(row.net_book_value), flt(row.acquisition_cost) * 0.85)
		if values:
			frappe.db.set_value("Fixed Asset", row.name, values, update_modified=False)
