# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Missing linen detection and shortage alerts."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import get_datetime


def create_linen_shortage_alert(batch_doc) -> str | None:
	missing = int(batch_doc.missing_quantity or 0)
	if missing <= 0:
		return None
	msg = _("LINEN SHORTAGE: {0} {1} missing (issued {2}, returned {3}).").format(
		missing,
		batch_doc.linen_type,
		batch_doc.issued_quantity,
		batch_doc.returned_quantity or 0,
	)
	key = f"linen-batch-{batch_doc.name}"
	if frappe.db.exists("Linen Shortage Alert", {"batch_reference": batch_doc.name, "status": "Open"}):
		return None
	alert = frappe.get_doc(
		{
			"doctype": "Linen Shortage Alert",
			"company": batch_doc.company,
			"branch": batch_doc.branch,
			"hotel_property": batch_doc.hotel_property,
			"linen_type": batch_doc.linen_type,
			"missing_quantity": missing,
			"issued_quantity": batch_doc.issued_quantity,
			"returned_quantity": batch_doc.returned_quantity or 0,
			"message": msg,
			"batch_reference": batch_doc.name,
			"alert_time": get_datetime(),
			"status": "Open",
			"alert_category": "Shortage",
		}
	)
	alert.insert(ignore_permissions=True)
	return alert.name


def detect_missing_linen_items(company: str, branch: str | None = None, hours: int = 48) -> list[dict]:
	"""Mark linen items as missing when not seen within threshold."""
	from frappe.utils import add_to_date, now_datetime

	since = add_to_date(now_datetime(), hours=-hours)
	filters: dict = {
		"company": company,
		"status": ["not in", ["Disposed", "Missing"]],
		"rfid_tag": ["is", "set"],
	}
	if branch:
		filters["branch"] = branch
	items = frappe.get_all(
		"Linen Item",
		filters=filters,
		fields=["name", "linen_name", "linen_type", "last_seen_at", "current_location"],
		limit=5000,
	)
	missing = []
	for row in items:
		if row.last_seen_at and get_datetime(row.last_seen_at) >= since:
			continue
		frappe.db.set_value("Linen Item", row.name, "status", "Missing", update_modified=False)
		missing.append(row)
	return missing
