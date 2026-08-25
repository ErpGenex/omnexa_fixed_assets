# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Resolve RFID Reader/Gateway registry entries by device id."""

from __future__ import annotations

import frappe
from frappe.utils import now_datetime

from omnexa_fixed_assets.utils.rfid.base import RFIDScanPayload


def resolve_reader(device_id: str | None) -> dict | None:
	device_id = (device_id or "").strip()
	if not device_id:
		return None
	row = frappe.db.get_value(
		"RFID Reader",
		{"reader_id": device_id},
		[
			"name",
			"reader_id",
			"reader_name",
			"company",
			"branch",
			"hotel_property",
			"hotel_room",
			"zone_text",
			"location_text",
			"provider",
			"rfid_gateway",
			"status",
		],
		as_dict=True,
	)
	return row


def touch_reader(device_id: str | None) -> None:
	device_id = (device_id or "").strip()
	if not device_id or not frappe.db.exists("RFID Reader", {"reader_id": device_id}):
		return
	frappe.db.set_value(
		"RFID Reader",
		{"reader_id": device_id},
		{"last_seen_at": now_datetime(), "status": "Online"},
		update_modified=False,
	)
	gateway = frappe.db.get_value("RFID Reader", {"reader_id": device_id}, "rfid_gateway")
	if gateway:
		frappe.db.set_value(
			"RFID Gateway",
			gateway,
			{"last_seen_at": now_datetime(), "status": "Online"},
			update_modified=False,
		)


def enrich_payload_from_reader(payload: RFIDScanPayload) -> RFIDScanPayload:
	reader = resolve_reader(payload.reader_device)
	if not reader:
		return payload
	location = payload.location_text or reader.location_text
	if reader.hotel_room and not location:
		location = reader.hotel_room
	if reader.zone_text and location:
		location = f"{reader.zone_text} / {location}" if location != reader.zone_text else reader.zone_text
	return RFIDScanPayload(
		asset=payload.asset,
		reader_device=payload.reader_device,
		location_text=location,
		signal_strength=payload.signal_strength,
		scan_result=payload.scan_result,
		rfid_tag=payload.rfid_tag,
	)
