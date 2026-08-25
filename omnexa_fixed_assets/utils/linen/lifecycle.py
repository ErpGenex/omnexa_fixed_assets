# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Linen lifecycle state transitions."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime


def apply_laundry_cycle(cycle_doc) -> None:
	"""Increment wash count and update linen status after laundry cycle."""
	linen = frappe.get_doc("Linen Item", cycle_doc.linen_item)
	prev_status = linen.status
	linen.wash_count = int(linen.wash_count or 0) + 1
	linen.status = "Washed" if cycle_doc.quality_result == "Pass" else linen.status
	if cycle_doc.quality_result == "Repair":
		linen.status = "Repair"
		linen.damage_count = int(linen.damage_count or 0) + 1
	elif cycle_doc.quality_result == "Dispose":
		linen.status = "Disposed"
	linen.last_laundry_cycle = cycle_doc.name
	linen.save(ignore_permissions=True)

	frappe.get_doc(
		{
			"doctype": "Linen Movement",
			"company": cycle_doc.company,
			"branch": cycle_doc.branch,
			"linen_item": linen.name,
			"movement_time": get_datetime(),
			"movement_type": "Laundry",
			"from_location": prev_status,
			"to_location": linen.status,
			"remarks": _("Laundry cycle #{0}").format(cycle_doc.cycle_number),
			"reference_doctype": "Linen Laundry Cycle",
			"reference_name": cycle_doc.name,
		}
	).insert(ignore_permissions=True)

	if linen.needs_replacement_warning():
		_create_replacement_warning(linen)


def _create_replacement_warning(linen) -> None:
	msg = _("Linen {0} has {1} wash cycles remaining.").format(
		linen.name, linen.remaining_wash_cycles()
	)
	if frappe.db.exists(
		"Asset Alert",
		{"message": msg, "status": "Open", "alert_type": "Capacity Warning"},
	):
		return
	# Asset Alert requires Fixed Asset link — use Linen Movement audit + optional custom alert path.
	frappe.logger().info("Linen replacement warning: %s", msg)


def record_linen_movement(
	linen_item: str,
	movement_type: str,
	*,
	to_location: str | None = None,
	from_location: str | None = None,
	reader_device: str | None = None,
	remarks: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
) -> str:
	linen = frappe.get_doc("Linen Item", linen_item)
	doc = frappe.get_doc(
		{
			"doctype": "Linen Movement",
			"company": linen.company,
			"branch": linen.branch,
			"linen_item": linen.name,
			"movement_time": now_datetime(),
			"movement_type": movement_type,
			"from_location": from_location or linen.current_location,
			"to_location": to_location,
			"hotel_property": linen.hotel_property,
			"hotel_room": linen.hotel_room,
			"reader_device": reader_device,
			"remarks": remarks,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name
