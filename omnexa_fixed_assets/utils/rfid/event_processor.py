# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""RFID event aggregation, deduplication, and movement detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_to_date, flt, get_datetime, now_datetime, today

from omnexa_fixed_assets.utils.rfid.base import RFIDScanPayload
from omnexa_fixed_assets.utils.rfid.reader_registry import enrich_payload_from_reader, touch_reader


@dataclass
class ProcessedRFIDEvent:
	ok: bool
	entity_type: str = "asset"
	asset: str | None = None
	linen_item: str | None = None
	scan_log: str | None = None
	scan_status: str | None = None
	duplicate: bool = False
	movement_created: bool = False
	movement_log: str | None = None
	alert_created: bool = False
	confidence_score: float = 0.0
	message: str | None = None


def _dedup_window_seconds() -> int:
	return int(frappe.conf.get("omnexa_rfid_dedup_seconds") or 30)


def resolve_asset_from_identifiers(
	asset: str | None = None,
	rfid_tag: str | None = None,
	epc: str | None = None,
	uid: str | None = None,
) -> str | None:
	candidate = (asset or "").strip()
	if candidate and frappe.db.exists("Fixed Asset", candidate):
		return candidate
	for tag in (rfid_tag, epc, uid):
		tag = (tag or "").strip()
		if not tag:
			continue
		name = frappe.db.get_value("Fixed Asset", {"rfid_tag": tag}, "name")
		if name:
			return name
	return None


def resolve_entity_from_identifiers(
	asset: str | None = None,
	rfid_tag: str | None = None,
	epc: str | None = None,
	uid: str | None = None,
) -> tuple[str, str] | None:
	tag = rfid_tag or epc or uid
	asset_name = resolve_asset_from_identifiers(asset, tag)
	if asset_name:
		return ("asset", asset_name)
	from omnexa_fixed_assets.utils.linen.rfid_processor import resolve_linen_from_tag

	linen = resolve_linen_from_tag(tag)
	if linen:
		return ("linen", linen)
	return None


def _confidence_score(payload: RFIDScanPayload, read_count: int = 1) -> float:
	base = 0.55
	if payload.reader_device:
		base += 0.15
	if payload.location_text:
		base += 0.1
	if payload.signal_strength is not None:
		base += min(0.15, abs(flt(payload.signal_strength)) / 100.0)
	base += min(0.15, read_count * 0.03)
	return round(min(base, 0.99), 2)


def _external_event_exists(external_event_id: str | None) -> bool:
	eid = (external_event_id or "").strip()
	if not eid:
		return False
	if not frappe.db.has_column("RFID Scan Log", "external_event_id"):
		return False
	return bool(frappe.db.exists("RFID Scan Log", {"external_event_id": eid}))


def _recent_duplicate(
	asset: str,
	rfid_tag: str | None,
	reader_device: str | None,
	location_text: str | None,
) -> bool:
	window = _dedup_window_seconds()
	since = add_to_date(now_datetime(), seconds=-window)
	filters: dict[str, Any] = {"fixed_asset": asset, "scan_time": [">=", since]}
	if reader_device:
		filters["reader_device"] = reader_device
	if rfid_tag:
		filters["rfid_tag"] = rfid_tag
	if location_text:
		filters["location_text"] = location_text
	return bool(frappe.db.exists("RFID Scan Log", filters))


def _last_scan(asset: str) -> dict | None:
	rows = frappe.get_all(
		"RFID Scan Log",
		filters={"fixed_asset": asset},
		fields=["name", "location_text", "reader_device", "scan_time", "scan_result"],
		order_by="scan_time desc",
		limit=1,
	)
	return rows[0] if rows else None


def _create_movement_log(asset_doc, payload: RFIDScanPayload, previous: dict | None, scan_log: str) -> str | None:
	prev_loc = (previous or {}).get("location_text") or ""
	curr_loc = (payload.location_text or "").strip()
	if not curr_loc or curr_loc == prev_loc:
		return None
	remarks = _("RFID movement: {0} → {1}").format(prev_loc or "?", curr_loc)
	log = frappe.get_doc(
		{
			"doctype": "Fixed Asset Movement Log",
			"company": asset_doc.company,
			"branch": asset_doc.branch,
			"posting_date": today(),
			"fixed_asset": asset_doc.name,
			"movement_type": "transfer",
			"remarks": remarks,
			"reference_doctype": "RFID Scan Log",
			"reference_name": scan_log,
		}
	)
	log.insert(ignore_permissions=True)
	return log.name


def _maybe_unauthorized_alert(asset_doc, payload: RFIDScanPayload) -> bool:
	if not frappe.conf.get("omnexa_rfid_unauthorized_alerts"):
		return False
	location = (payload.location_text or "").lower()
	suspicious = ("loading", "disposal", "exit", "gate-out", "unauthorized")
	if not any(token in location for token in suspicious):
		return False
	if frappe.db.exists(
		"Asset Alert",
		{"asset": asset_doc.name, "alert_type": "Unauthorized Movement", "status": "Open"},
	):
		return False
	alert = frappe.get_doc(
		{
			"doctype": "Asset Alert",
			"company": asset_doc.company,
			"branch": asset_doc.branch,
			"asset": asset_doc.name,
			"alert_time": now_datetime(),
			"alert_type": "Unauthorized Movement",
			"severity": "Critical",
			"status": "Open",
			"message": _("RFID detected asset at {0}").format(payload.location_text),
			"source": "rfid_event_processor",
		}
	)
	alert.insert(ignore_permissions=True)
	return True


def process_rfid_scan(
	payload: RFIDScanPayload,
	*,
	provider: str | None = None,
	notes: str | None = None,
	skip_dedup: bool = False,
	external_event_id: str | None = None,
	sequence_number: int | None = None,
) -> ProcessedRFIDEvent:
	payload = enrich_payload_from_reader(payload)
	touch_reader(payload.reader_device)

	if _external_event_exists(external_event_id):
		return ProcessedRFIDEvent(
			ok=True,
			duplicate=True,
			confidence_score=_confidence_score(payload),
			message=_("Offline event already synced."),
		)

	entity = resolve_entity_from_identifiers(payload.asset, payload.rfid_tag)
	if not entity:
		return ProcessedRFIDEvent(ok=False, message=_("No asset or linen found for RFID tag."))

	entity_type, entity_name = entity
	if entity_type == "linen":
		from omnexa_fixed_assets.utils.linen.rfid_processor import process_linen_rfid_scan

		out = process_linen_rfid_scan(payload, skip_dedup=skip_dedup)
		return ProcessedRFIDEvent(
			ok=out.ok,
			entity_type="linen",
			linen_item=out.linen_item,
			duplicate=out.duplicate,
			movement_created=bool(out.movement),
			movement_log=out.movement,
			confidence_score=_confidence_score(payload),
			message=out.message,
		)

	asset_name = entity_name
	asset_doc = frappe.get_doc("Fixed Asset", asset_name)
	tag = (payload.rfid_tag or asset_doc.get("rfid_tag") or "").strip() or None

	if not skip_dedup and _recent_duplicate(asset_name, tag, payload.reader_device, payload.location_text):
		return ProcessedRFIDEvent(
			ok=True,
			entity_type="asset",
			asset=asset_name,
			duplicate=True,
			confidence_score=_confidence_score(payload),
			message=_("Duplicate read suppressed."),
		)

	previous = _last_scan(asset_name)
	log_data: dict[str, Any] = {
		"doctype": "RFID Scan Log",
		"company": asset_doc.company,
		"branch": asset_doc.branch,
		"fixed_asset": asset_doc.name,
		"rfid_tag": tag,
		"reader_device": payload.reader_device,
		"location_text": payload.location_text,
		"signal_strength": payload.signal_strength,
		"scan_result": payload.scan_result or "Seen",
		"notes": notes or (f"provider={provider}" if provider else None),
	}
	if external_event_id and frappe.db.has_column("RFID Scan Log", "external_event_id"):
		log_data["external_event_id"] = external_event_id
	if sequence_number is not None and frappe.db.has_column("RFID Scan Log", "sequence_number"):
		log_data["sequence_number"] = sequence_number
	log = frappe.get_doc(log_data)
	log.insert(ignore_permissions=True)

	updates = {"scan_status": log.scan_result, "last_inventory_scan_at": log.scan_time}
	if tag and not (asset_doc.get("rfid_tag") or "").strip():
		updates["rfid_tag"] = tag
	asset_doc.db_set(updates, update_modified=False)

	movement_log = _create_movement_log(asset_doc, payload, previous, log.name)
	alert_created = _maybe_unauthorized_alert(asset_doc, payload)

	try:
		frappe.publish_realtime(
			"omnexa_rfid_movement",
			{
				"entity_type": "asset",
				"asset": asset_doc.name,
				"location": payload.location_text,
				"reader": payload.reader_device,
				"scan_log": log.name,
				"duplicate": False,
			},
			doctype="Fixed Asset",
			docname=asset_doc.name,
			after_commit=True,
		)
	except Exception:
		pass

	return ProcessedRFIDEvent(
		ok=True,
		entity_type="asset",
		asset=asset_doc.name,
		scan_log=log.name,
		scan_status=log.scan_result,
		movement_created=bool(movement_log),
		movement_log=movement_log,
		alert_created=alert_created,
		confidence_score=_confidence_score(payload),
	)


def process_rfid_events_bulk(events: list[dict], *, provider: str | None = None) -> dict:
	from omnexa_fixed_assets.utils.rfid.factory import get_rfid_adapter

	adapter = get_rfid_adapter(provider)
	results = []
	for raw in events or []:
		if not isinstance(raw, dict):
			continue
		tag = raw.get("rfid_tag") or raw.get("epc") or raw.get("uid")
		entity = resolve_entity_from_identifiers(raw.get("asset"), tag)
		asset_name = entity[1] if entity and entity[0] == "asset" else raw.get("asset")
		normalized = adapter.normalize_scan({**raw, "asset": asset_name or "", "rfid_tag": tag})
		out = process_rfid_scan(
			normalized,
			provider=provider,
			notes=raw.get("notes"),
			external_event_id=raw.get("external_event_id") or raw.get("event_id"),
			sequence_number=raw.get("sequence_number"),
		)
		results.append(
			{
				"ok": out.ok,
				"entity_type": out.entity_type,
				"asset": out.asset,
				"linen_item": out.linen_item,
				"scan_log": out.scan_log,
				"duplicate": out.duplicate,
				"movement_log": out.movement_log,
				"confidence_score": out.confidence_score,
				"message": out.message,
			}
		)
	return {
		"processed": len(results),
		"created": sum(1 for r in results if r.get("scan_log") or r.get("linen_item")),
		"duplicates": sum(1 for r in results if r.get("duplicate")),
		"results": results,
	}


def get_live_movements(company: str, branch: str | None = None, limit: int = 50) -> list[dict]:
	filters: dict[str, Any] = {"company": company}
	if branch:
		filters["branch"] = branch
	out: list[dict] = []

	asset_rows = frappe.get_all(
		"Fixed Asset Movement Log",
		filters=filters,
		fields=["name", "fixed_asset", "remarks", "reference_doctype", "reference_name", "creation"],
		order_by="creation desc",
		limit=limit,
	)
	for row in asset_rows:
		if row.reference_doctype not in ("RFID Scan Log", "Hotel Asset Transfer", None):
			continue
		asset_meta = frappe.db.get_value(
			"Fixed Asset",
			row.fixed_asset,
			["asset_name", "hotel_property", "hotel_room", "hotel_zone"],
			as_dict=True,
		) or {}
		out.append(
			{
				"entity_type": "asset",
				"timestamp": str(row.creation),
				"asset": row.fixed_asset,
				"asset_name": asset_meta.get("asset_name"),
				"hotel_property": asset_meta.get("hotel_property"),
				"hotel_room": asset_meta.get("hotel_room"),
				"hotel_zone": asset_meta.get("hotel_zone"),
				"remarks": row.remarks,
			}
		)

	linen_filters = dict(filters)
	linen_rows = frappe.get_all(
		"Linen Movement",
		filters=linen_filters,
		fields=["name", "linen_item", "to_location", "movement_type", "creation"],
		order_by="creation desc",
		limit=limit,
	)
	for row in linen_rows:
		out.append(
			{
				"entity_type": "linen",
				"timestamp": str(row.creation),
				"linen_item": row.linen_item,
				"location": row.to_location,
				"movement_type": row.movement_type,
			}
		)

	out.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
	return out[:limit]


def get_live_map_payload(company: str, branch: str | None = None) -> dict:
	"""Floor/room grouped positions for live map UI."""
	filters: dict[str, Any] = {"company": company, "docstatus": ["<", 2]}
	if branch:
		filters["branch"] = branch
	assets = frappe.get_all(
		"Fixed Asset",
		filters={**filters, "hotel_room": ["is", "set"]},
		fields=["name", "asset_name", "hotel_property", "hotel_room", "hotel_zone", "scan_status", "rfid_tag"],
		limit=500,
	)
	rooms = frappe.get_all(
		"Hotel Room",
		filters={"company": company, **({"branch": branch} if branch else {})},
		fields=["name", "room_number", "floor", "wing", "hotel_property", "status"],
		limit=500,
	)
	readers = []
	if frappe.db.exists("DocType", "RFID Reader"):
		readers = frappe.get_all(
			"RFID Reader",
			filters={"company": company, **({"branch": branch} if branch else {})},
			fields=["name", "reader_id", "reader_name", "status", "zone_text", "location_text", "hotel_room"],
			limit=200,
		)
	return {
		"assets": assets,
		"rooms": rooms,
		"readers": readers,
		"movements": get_live_movements(company, branch, limit=30),
	}
