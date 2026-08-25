# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Global multi-property hospitality portfolio aggregation."""

from __future__ import annotations

import frappe
from frappe.utils import flt


def get_global_portfolio(company: str) -> dict:
	"""Cross-branch/property KPI rollup for enterprise command center."""
	properties = frappe.get_all(
		"Hotel Property",
		filters={"company": company, "is_active": 1},
		fields=["name", "property_name", "branch", "brand", "location", "total_rooms", "operational_status"],
		order_by="property_name asc",
	)
	branches = frappe.get_all("Branch", filters={"company": company}, pluck="name")

	rollup = {
		"total_properties": len(properties),
		"total_branches": len(branches),
		"total_assets": frappe.db.count("Fixed Asset", {"company": company}),
		"rfid_tagged": frappe.db.count("Fixed Asset", {"company": company, "rfid_tag": ["is", "set"]}),
		"missing_assets": frappe.db.count(
			"Fixed Asset", {"company": company, "scan_status": ["in", ["Missing", "Mismatch"]]}
		),
		"total_linen": 0,
		"missing_linen": 0,
		"rfid_online": 0,
		"rfid_offline": 0,
		"open_alerts": frappe.db.count("Asset Alert", {"company": company, "status": "Open"}),
		"open_recommendations": frappe.db.count(
			"Asset Recommendation", {"company": company, "status": "Open"}
		),
	}

	if frappe.db.exists("DocType", "Linen Item"):
		rollup["total_linen"] = frappe.db.count("Linen Item", {"company": company})
		rollup["missing_linen"] = frappe.db.count("Linen Item", {"company": company, "status": "Missing"})
	if frappe.db.exists("DocType", "RFID Reader"):
		rollup["rfid_online"] = frappe.db.count("RFID Reader", {"company": company, "status": "Online"})
		rollup["rfid_offline"] = frappe.db.count("RFID Reader", {"company": company, "status": "Offline"})

	property_rows = []
	for prop in properties:
		pf = {"company": company, "hotel_property": prop.name}
		property_rows.append(
			{
				"property": prop.name,
				"property_name": prop.property_name,
				"branch": prop.branch,
				"brand": prop.brand,
				"location": prop.location,
				"total_rooms": prop.total_rooms,
				"operational_status": prop.operational_status,
				"assets": frappe.db.count("Fixed Asset", pf),
				"rfid_tagged": frappe.db.count("Fixed Asset", {**pf, "rfid_tag": ["is", "set"]}),
				"missing_assets": frappe.db.count(
					"Fixed Asset", {**pf, "scan_status": ["in", ["Missing", "Mismatch"]]}
				),
				"linen": frappe.db.count("Linen Item", pf) if frappe.db.exists("DocType", "Linen Item") else 0,
				"health_avg": _avg_health(company, prop.name),
			}
		)

	branch_rows = []
	for branch in branches:
		bf = {"company": company, "branch": branch}
		branch_rows.append(
			{
				"branch": branch,
				"assets": frappe.db.count("Fixed Asset", bf),
				"properties": frappe.db.count("Hotel Property", {**bf, "is_active": 1}),
				"missing_assets": frappe.db.count(
					"Fixed Asset", {**bf, "scan_status": ["in", ["Missing", "Mismatch"]]}
				),
			}
		)

	return {
		"rollup": rollup,
		"properties": property_rows,
		"branches": branch_rows,
	}


def _avg_health(company: str, hotel_property: str) -> float:
	row = frappe.db.sql(
		"""
		select avg(coalesce(health_score, 0)) as avg_score
		from `tabFixed Asset`
		where company=%s and hotel_property=%s
		""",
		(company, hotel_property),
		as_dict=True,
	)
	return round(flt(row[0].avg_score if row else 0), 1)


def get_floor_plan_svg(company: str, branch: str | None, floor: str, hotel_property: str | None = None) -> dict | None:
	filters: dict = {"company": company, "floor": floor, "is_active": 1}
	if branch:
		filters["branch"] = branch
	if hotel_property:
		filters["hotel_property"] = hotel_property
	rows = frappe.get_all(
		"Hotel Floor Plan",
		filters=filters,
		fields=["name", "svg_content", "attach_image", "hotel_property", "floor_label"],
		limit=1,
	)
	if not rows:
		return None
	row = rows[0]
	return {
		"name": row.name,
		"hotel_property": row.hotel_property,
		"floor": floor,
		"floor_label": row.floor_label,
		"svg_content": row.svg_content,
		"attach_image": row.attach_image,
	}
