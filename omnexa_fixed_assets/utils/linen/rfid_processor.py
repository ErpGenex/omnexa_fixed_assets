# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Process RFID scans for Linen Items."""

from __future__ import annotations

from dataclasses import dataclass

import frappe
from frappe import _
from frappe.utils import now_datetime

from omnexa_fixed_assets.utils.linen.lifecycle import record_linen_movement
from omnexa_fixed_assets.utils.rfid.base import RFIDScanPayload


@dataclass
class ProcessedLinenRFIDEvent:
	ok: bool
	linen_item: str | None = None
	movement: str | None = None
	duplicate: bool = False
	message: str | None = None


def resolve_linen_from_tag(rfid_tag: str | None) -> str | None:
	tag = (rfid_tag or "").strip()
	if not tag:
		return None
	return frappe.db.get_value("Linen Item", {"rfid_tag": tag}, "name")


def process_linen_rfid_scan(
	payload: RFIDScanPayload,
	*,
	reader_device: str | None = None,
	skip_dedup: bool = False,
) -> ProcessedLinenRFIDEvent:
	linen_name = resolve_linen_from_tag(payload.rfid_tag)
	if not linen_name:
		return ProcessedLinenRFIDEvent(ok=False, message=_("Linen item not found for RFID tag."))

	linen = frappe.get_doc("Linen Item", linen_name)
	location = (payload.location_text or "").strip()
	prev = (linen.current_location or "").strip()

	if not skip_dedup and location and location == prev:
		return ProcessedLinenRFIDEvent(
			ok=True,
			linen_item=linen.name,
			duplicate=True,
			message=_("Duplicate linen read suppressed."),
		)

	updates = {
		"last_seen_at": now_datetime(),
		"last_reader": reader_device or payload.reader_device,
	}
	if location:
		updates["current_location"] = location
	if linen.status in ("Purchased", "Tagged", "Clean Storage"):
		updates["status"] = "In Use"
	elif linen.status == "Missing":
		updates["status"] = "In Use"
	linen.db_set(updates, update_modified=False)

	movement = None
	if location and location != prev:
		movement = record_linen_movement(
			linen.name,
			"RFID Scan",
			from_location=prev or None,
			to_location=location,
			reader_device=reader_device or payload.reader_device,
			remarks=_("RFID scan at {0}").format(location),
		)
		try:
			frappe.publish_realtime(
				"omnexa_linen_movement",
				{
					"linen_item": linen.name,
					"location": location,
					"reader": reader_device or payload.reader_device,
					"movement": movement,
				},
				doctype="Linen Item",
				docname=linen.name,
				after_commit=True,
			)
		except Exception:
			pass

	return ProcessedLinenRFIDEvent(ok=True, linen_item=linen.name, movement=movement)
