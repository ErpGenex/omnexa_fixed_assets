# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Floor/zone heatmap density for hospitality dashboards."""

from __future__ import annotations

import frappe
from frappe.utils import add_to_date, now_datetime


def get_asset_heatmap(company: str, branch: str | None = None, floor: str | None = None) -> dict:
	"""Asset/movement/failure/loss density by floor and zone."""
	filters: dict = {"company": company}
	if branch:
		filters["branch"] = branch
	room_filters = dict(filters)
	if floor:
		room_filters["floor"] = floor

	rooms = frappe.get_all(
		"Hotel Room",
		filters=room_filters,
		fields=["name", "room_number", "floor", "wing", "hotel_property"],
		limit=1000,
	)
	room_names = [r.name for r in rooms]
	if not room_names:
		return {"floors": [], "zones": [], "cells": []}

	asset_counts = frappe.db.sql(
		"""
		select hotel_room, count(*) as asset_count
		from `tabFixed Asset`
		where company=%(company)s
		{branch_sql}
		and hotel_room in %(rooms)s
		group by hotel_room
		""".format(branch_sql="and branch=%(branch)s" if branch else ""),
		{**filters, "rooms": room_names},
		as_dict=True,
	)
	asset_map = {r.hotel_room: r.asset_count for r in asset_counts}

	since = add_to_date(now_datetime(), hours=-24)
	movement_counts = frappe.db.sql(
		"""
		select fa.hotel_room, count(*) as movement_count
		from `tabFixed Asset Movement Log` ml
		inner join `tabFixed Asset` fa on fa.name = ml.fixed_asset
		where ml.company=%(company)s
		{branch_sql}
		and fa.hotel_room in %(rooms)s
		and ml.creation >= %(since)s
		group by fa.hotel_room
		""".format(branch_sql="and ml.branch=%(branch)s" if branch else ""),
		{**filters, "rooms": room_names, "since": since},
		as_dict=True,
	)
	move_map = {r.hotel_room: r.movement_count for r in movement_counts}

	failure_counts = frappe.db.sql(
		"""
		select fa.hotel_room, count(*) as failure_count
		from `tabAsset Failure Event` fe
		inner join `tabFixed Asset` fa on fa.name = fe.asset
		where fe.company=%(company)s
		{branch_sql}
		and fa.hotel_room in %(rooms)s
		group by fa.hotel_room
		""".format(branch_sql="and fe.branch=%(branch)s" if branch else ""),
		{**filters, "rooms": room_names},
		as_dict=True,
	)
	fail_map = {r.hotel_room: r.failure_count for r in failure_counts}

	missing_counts = frappe.db.sql(
		"""
		select hotel_room, count(*) as loss_count
		from `tabFixed Asset`
		where company=%(company)s
		{branch_sql}
		and hotel_room in %(rooms)s
		and scan_status in ('Missing', 'Mismatch')
		group by hotel_room
		""".format(branch_sql="and branch=%(branch)s" if branch else ""),
		{**filters, "rooms": room_names},
		as_dict=True,
	)
	loss_map = {r.hotel_room: r.loss_count for r in missing_counts}

	cells = []
	floor_set: set[str] = set()
	zone_set: set[str] = set()
	for room in rooms:
		floor_val = room.floor or "Unknown"
		zone_val = room.wing or floor_val
		floor_set.add(floor_val)
		zone_set.add(zone_val)
		cells.append(
			{
				"room": room.name,
				"room_number": room.room_number,
				"floor": floor_val,
				"zone": zone_val,
				"hotel_property": room.hotel_property,
				"asset_density": int(asset_map.get(room.name) or 0),
				"movement_density": int(move_map.get(room.name) or 0),
				"failure_density": int(fail_map.get(room.name) or 0),
				"loss_density": int(loss_map.get(room.name) or 0),
			}
		)

	return {
		"floors": sorted(floor_set),
		"zones": sorted(zone_set),
		"cells": cells,
	}
