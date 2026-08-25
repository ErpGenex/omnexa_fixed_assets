# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Seed linen items, readers, and sample batches for QA."""

from __future__ import annotations

import frappe
from frappe.utils import add_days, now_datetime, today


def run(company: str, branch: str, count: int = 50):
	prop = frappe.get_all("Hotel Property", filters={"company": company, "branch": branch}, pluck="name", limit=1)
	hotel_property = prop[0] if prop else None
	rooms = frappe.get_all(
		"Hotel Room",
		filters={"company": company, "branch": branch},
		pluck="name",
		limit=10,
	)

	# RFID infrastructure
	if not frappe.db.exists("RFID Gateway", {"gateway_id": f"GW-{branch}"}):
		frappe.get_doc(
			{
				"doctype": "RFID Gateway",
				"company": company,
				"branch": branch,
				"gateway_id": f"GW-{branch}",
				"gateway_name": f"Gateway {branch}",
				"provider": "generic",
				"hotel_property": hotel_property,
				"location_text": "Main Lobby",
			}
		).insert(ignore_permissions=True)

	for idx in range(3):
		rid = f"READER-{branch}-{idx + 1}"
		if frappe.db.exists("RFID Reader", {"reader_id": rid}):
			continue
		frappe.get_doc(
			{
				"doctype": "RFID Reader",
				"company": company,
				"branch": branch,
				"reader_id": rid,
				"reader_name": f"Reader {idx + 1}",
				"reader_type": "Fixed",
				"provider": "generic",
				"rfid_gateway": f"GW-{branch}",
				"hotel_property": hotel_property,
				"hotel_room": rooms[idx % len(rooms)] if rooms else None,
				"zone_text": f"Zone-{idx + 1}",
				"location_text": rooms[idx % len(rooms)] if rooms else f"Zone-{idx + 1}",
			}
		).insert(ignore_permissions=True)

	linen_types = ["Bath Towel", "Hand Towel", "Bedsheet", "Pillowcase"]
	created = 0
	for i in range(int(count or 50)):
		tag = f"LIN-RFID-{branch}-{i + 1:04d}"
		if frappe.db.exists("Linen Item", {"rfid_tag": tag}):
			continue
		lt = linen_types[i % len(linen_types)]
		doc = frappe.get_doc(
			{
				"doctype": "Linen Item",
				"company": company,
				"branch": branch,
				"linen_name": f"{lt} #{i + 1}",
				"linen_type": lt,
				"department": "Housekeeping",
				"status": "Tagged",
				"rfid_tag": tag,
				"hotel_property": hotel_property,
				"hotel_room": rooms[i % len(rooms)] if rooms else None,
				"current_location": rooms[i % len(rooms)] if rooms else "Linen Room",
				"purchase_date": add_days(today(), -120),
				"wash_count": i % 190,
				"expected_life_cycles": 200,
			}
		)
		doc.insert(ignore_permissions=True)
		created += 1

	batch_name = None
	if not frappe.db.exists("Linen Issue Batch", {"company": company, "branch": branch, "docstatus": 1}):
		batch = frappe.get_doc(
			{
				"doctype": "Linen Issue Batch",
				"company": company,
				"branch": branch,
				"posting_date": today(),
				"hotel_property": hotel_property,
				"linen_type": "Bath Towel",
				"department": "Housekeeping",
				"issued_quantity": 500,
				"returned_quantity": 473,
			}
		)
		batch.insert(ignore_permissions=True)
		batch.submit()
		batch_name = batch.name

	return {
		"ok": True,
		"company": company,
		"branch": branch,
		"linen_created": created,
		"readers": 3,
		"sample_batch": batch_name,
	}
