# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Seed sample SVG floor plans for live map."""

from __future__ import annotations

import frappe


SAMPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" width="100%" height="auto">
  <rect width="800" height="500" fill="#f8f9fa" stroke="#dee2e6"/>
  <text x="20" y="30" font-size="16" fill="#495057">Hotel Floor Plan</text>
  <rect x="40" y="60" width="150" height="100" fill="#e8f4fd" stroke="#0d6efd" data-room="101"/>
  <text x="90" y="115" text-anchor="middle" font-size="14">101</text>
  <rect x="210" y="60" width="150" height="100" fill="#e8f4fd" stroke="#0d6efd" data-room="102"/>
  <text x="285" y="115" text-anchor="middle" font-size="14">102</text>
  <rect x="380" y="60" width="150" height="100" fill="#fff3cd" stroke="#ffc107" data-room="103"/>
  <text x="455" y="115" text-anchor="middle" font-size="14">103</text>
  <rect x="40" y="180" width="320" height="80" fill="#fde2e2" stroke="#dc3545" data-zone="corridor"/>
  <text x="200" y="225" text-anchor="middle" font-size="12">Corridor</text>
  <rect x="40" y="280" width="150" height="100" fill="#d1e7dd" stroke="#198754" data-room="104"/>
  <text x="115" y="335" text-anchor="middle" font-size="14">104</text>
  <rect x="210" y="280" width="150" height="100" fill="#d1e7dd" stroke="#198754" data-room="105"/>
  <text x="285" y="335" text-anchor="middle" font-size="14">105</text>
</svg>"""


def run(company: str, branch: str, hotel_property: str | None = None, floor: str = "1"):
	prop = hotel_property
	if not prop:
		props = frappe.get_all(
			"Hotel Property", filters={"company": company, "branch": branch}, pluck="name", limit=1
		)
		prop = props[0] if props else None
	if not prop:
		return {"ok": False, "message": "No hotel property found."}

	name = f"{prop}-{floor}"
	if frappe.db.exists("Hotel Floor Plan", name):
		return {"ok": True, "created": False, "name": name}

	doc = frappe.get_doc(
		{
			"doctype": "Hotel Floor Plan",
			"company": company,
			"branch": branch,
			"hotel_property": prop,
			"floor": floor,
			"floor_label": f"Floor {floor}",
			"is_active": 1,
			"svg_content": SAMPLE_SVG,
		}
	)
	doc.insert(ignore_permissions=True)
	return {"ok": True, "created": True, "name": doc.name}
