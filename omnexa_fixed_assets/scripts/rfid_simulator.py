# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Simulate RFID gateway bursts for QA (idempotent-friendly)."""

from __future__ import annotations

import frappe
from frappe.utils import now_datetime


def run(company: str, branch: str, count: int = 20, provider: str = "generic"):
	from omnexa_fixed_assets.utils.rfid.event_processor import process_rfid_events_bulk

	assets = frappe.get_all(
		"Fixed Asset",
		filters={"company": company, "branch": branch, "docstatus": ["<", 2]},
		fields=["name", "rfid_tag", "hotel_room"],
		limit=int(count or 20),
	)
	if not assets:
		return {"ok": False, "message": "No assets found."}

	events = []
	for idx, row in enumerate(assets):
		tag = (row.rfid_tag or f"SIM-{row.name}").strip()
		room = row.hotel_room or f"Zone-{idx % 5}"
		events.append(
			{
				"asset": row.name,
				"rfid_tag": tag,
				"reader_device": f"SIM-READER-{idx % 3}",
				"location_text": room,
				"signal_strength": 70 + (idx % 10),
				"scan_time": str(now_datetime()),
			}
		)
		# Second pass: duplicate to exercise dedup
		if idx % 4 == 0:
			events.append(events[-1].copy())

	result = process_rfid_events_bulk(events, provider=provider)
	return {"ok": True, "company": company, "branch": branch, **result}
