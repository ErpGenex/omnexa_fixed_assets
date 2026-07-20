# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Form dashboard connections for hotel master data (Property Master / Room mapping UX)."""

import frappe
from frappe import _


def extend_hotel_property_dashboard(data=None):
	data = frappe._dict(data or {})
	data.transactions = list(data.get("transactions") or [])
	data.transactions.extend(
		[
			{"label": _("Hotel Structure"), "items": ["Hotel Room", "Hotel Functional Area"]},
			{"label": _("Hotel Assets & Inspections"), "items": ["Fixed Asset", "Hotel Asset Inspection"]},
		]
	)
	ns = frappe._dict(data.get("non_standard_fieldnames") or {})
	ns.update(
		{
			"Hotel Room": "hotel_property",
			"Hotel Functional Area": "hotel_property",
			"Fixed Asset": "hotel_property",
			"Hotel Asset Inspection": "hotel_property"
	}
	)
	data.non_standard_fieldnames = ns
	return data


def extend_hotel_room_dashboard(data=None):
	data = frappe._dict(data or {})
	data.transactions = list(data.get("transactions") or [])
	data.transactions.append({"label": _("Room Assets"), "items": ["Fixed Asset", "Hotel Asset Inspection"]})
	ns = frappe._dict(data.get("non_standard_fieldnames") or {})
	ns.update(
		{
			"Fixed Asset": "hotel_room",
			"Hotel Asset Inspection": "hotel_room"
	}
	)
	data.non_standard_fieldnames = ns
	return data
