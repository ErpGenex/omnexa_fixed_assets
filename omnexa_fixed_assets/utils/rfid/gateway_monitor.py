# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Mark RFID gateways/readers offline when not seen recently."""

from __future__ import annotations

import frappe
from frappe.utils import add_to_date, now_datetime


def mark_stale_rfid_devices_offline(hours: int = 2) -> dict:
	if not frappe.db.exists("DocType", "RFID Gateway"):
		return {"gateways": 0, "readers": 0}
	since = add_to_date(now_datetime(), hours=-hours)
	gw_count = 0
	for row in frappe.get_all(
		"RFID Gateway",
		filters={"status": "Online"},
		fields=["name", "gateway_id", "last_seen_at", "company", "branch"],
	):
		last = row.last_seen_at
		if last and last >= since:
			continue
		frappe.db.set_value("RFID Gateway", row.name, "status", "Offline", update_modified=False)
		gw_count += 1
		_log_offline(row.company, row.branch, "RFID Gateway", row.gateway_id)

	rd_count = 0
	for row in frappe.get_all(
		"RFID Reader",
		filters={"status": "Online"},
		fields=["name", "reader_id", "last_seen_at", "company", "branch"],
	):
		last = row.last_seen_at
		if last and last >= since:
			continue
		frappe.db.set_value("RFID Reader", row.name, "status", "Offline", update_modified=False)
		rd_count += 1
		_log_offline(row.company, row.branch, "RFID Reader", row.reader_id)

	return {"gateways": gw_count, "readers": rd_count}


def _log_offline(company: str, branch: str | None, entity_type: str, entity_name: str) -> None:
	try:
		from omnexa_fixed_assets.utils.intelligence.rules_engine import log_intelligence_audit

		log_intelligence_audit(
			company,
			"Gateway Offline",
			f"{entity_type} {entity_name} marked offline",
			branch=branch,
			entity_type=entity_type,
			entity_name=entity_name,
			source="System Automation",
			device=entity_name,
		)
	except Exception:
		pass
