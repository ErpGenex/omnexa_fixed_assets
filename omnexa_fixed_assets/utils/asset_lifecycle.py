# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe
from frappe.utils import getdate


def get_asset_lifecycle_timeline(asset: str, limit: int = 50) -> list[dict]:
	"""Unified lifecycle events for desk timeline and mobile API."""
	if not asset or not frappe.db.exists("Fixed Asset", asset):
		return []

	events: list[dict] = []
	asset_row = frappe.db.get_value(
		"Fixed Asset",
		asset,
		["creation", "capitalization_date", "status", "hotel_property", "hotel_room"],
		as_dict=True,
	) or {}

	if asset_row.get("capitalization_date"):
		events.append(
			{
				"date": str(asset_row.capitalization_date),
				"event_type": "Capitalization",
				"title": "Asset capitalized",
				"reference_doctype": "Fixed Asset",
				"reference_name": asset,
				"detail": asset_row.status or "",
			}
		)

	for row in frappe.get_all(
		"Fixed Asset Movement Log",
		filters={"fixed_asset": asset},
		fields=["posting_date", "movement_type", "remarks", "reference_doctype", "reference_name", "creation"],
		order_by="posting_date desc, creation desc",
		limit=limit,
	):
		events.append(
			{
				"date": str(row.posting_date or getdate(row.creation)),
				"event_type": (row.movement_type or "movement").title(),
				"title": row.remarks or row.movement_type or "Movement",
				"reference_doctype": row.reference_doctype,
				"reference_name": row.reference_name,
				"detail": "",
			}
		)

	for row in frappe.get_all(
		"Hotel Asset Transfer",
		filters={"fixed_asset": asset, "docstatus": 1},
		fields=["posting_date", "name", "from_hotel_room", "to_hotel_room"],
		order_by="posting_date desc",
		limit=limit,
	):
		events.append(
			{
				"date": str(row.posting_date),
				"event_type": "Transfer",
				"title": f"{row.from_hotel_room or '?'} → {row.to_hotel_room or '?'}",
				"reference_doctype": "Hotel Asset Transfer",
				"reference_name": row.name,
				"detail": "",
			}
		)

	for row in frappe.get_all(
		"Hotel Asset Inspection",
		filters={"fixed_asset": asset},
		fields=["inspection_date", "name", "condition_status"],
		order_by="inspection_date desc",
		limit=limit,
	):
		events.append(
			{
				"date": str(row.inspection_date),
				"event_type": "Inspection",
				"title": f"Condition: {row.condition_status}",
				"reference_doctype": "Hotel Asset Inspection",
				"reference_name": row.name,
				"detail": "",
			}
		)

	for row in frappe.get_all(
		"Fixed Asset Depreciation Entry",
		filters={"fixed_asset": asset, "docstatus": 1},
		fields=["posting_date", "name", "depreciation_amount"],
		order_by="posting_date desc",
		limit=limit,
	):
		events.append(
			{
				"date": str(row.posting_date),
				"event_type": "Depreciation",
				"title": f"Depreciation {row.depreciation_amount}",
				"reference_doctype": "Fixed Asset Depreciation Entry",
				"reference_name": row.name,
				"detail": "",
			}
		)

	for row in frappe.get_all(
		"RFID Scan Log",
		filters={"fixed_asset": asset},
		fields=["scan_time", "name", "scan_result", "location_text"],
		order_by="scan_time desc",
		limit=min(limit, 20),
	):
		events.append(
			{
				"date": str(getdate(row.scan_time)),
				"event_type": "RFID Scan",
				"title": f"{row.scan_result or 'Scan'} @ {row.location_text or ''}".strip(),
				"reference_doctype": "RFID Scan Log",
				"reference_name": row.name,
				"detail": "",
			}
		)

	# De-dupe by reference and sort newest first
	seen: set[tuple] = set()
	unique: list[dict] = []
	for ev in sorted(events, key=lambda x: (x.get("date") or "", x.get("title") or ""), reverse=True):
		key = (ev.get("reference_doctype"), ev.get("reference_name"), ev.get("event_type"))
		if key in seen and key[1]:
			continue
		seen.add(key)
		unique.append(ev)
	return unique[:limit]
