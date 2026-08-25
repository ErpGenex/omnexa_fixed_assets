# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe


def get_branch_brand_location(branch: str | None) -> dict[str, str]:
	"""Derive hotel brand / location labels from branch master data."""
	if not branch or not frappe.db.exists("Branch", branch):
		return {"brand": "", "location": ""}

	row = frappe.db.get_value(
		"Branch",
		branch,
		[
			"eta_company_trade_name",
			"branch_name",
			"eta_address_city",
			"eta_address_governate",
			"eta_address_country",
			"zatca_city",
		],
		as_dict=True,
	) or {}

	brand = (row.get("eta_company_trade_name") or row.get("branch_name") or "").strip()
	location_parts = [
		row.get("eta_address_city") or row.get("zatca_city"),
		row.get("eta_address_governate"),
		row.get("eta_address_country"),
	]
	location = ", ".join(part.strip() for part in location_parts if part and str(part).strip())
	if not location:
		location = (row.get("branch_name") or "").strip()

	return {"brand": brand, "location": location}


def apply_hotel_property_branch_defaults(doc) -> None:
	"""Fill brand/location on Hotel Property from branch when empty."""
	if not doc.get("branch"):
		return
	defaults = get_branch_brand_location(doc.branch)
	if not (doc.get("brand") or "").strip() and defaults["brand"]:
		doc.brand = defaults["brand"]
	if not (doc.get("location") or "").strip() and defaults["location"]:
		doc.location = defaults["location"]


def sync_company_branch_from_hotel_property(doc) -> None:
	"""Align company/branch with selected hotel property."""
	if not doc.get("hotel_property"):
		return
	prop = frappe.db.get_value(
		"Hotel Property",
		doc.hotel_property,
		["company", "branch"],
		as_dict=True,
	)
	if not prop:
		return
	if prop.get("company"):
		doc.company = prop["company"]
	if prop.get("branch"):
		doc.branch = prop["branch"]


def sync_hotel_fields_from_fixed_asset(
	doc,
	*,
	property_field: str = "hotel_property",
	room_field: str = "hotel_room",
	only_if_empty: bool = True,
) -> None:
	"""Copy hotel placement from Fixed Asset onto a child document."""
	asset_name = doc.get("fixed_asset") or doc.get("asset")
	if not asset_name:
		return

	asset = frappe.db.get_value(
		"Fixed Asset",
		asset_name,
		["hotel_property", "hotel_room"],
		as_dict=True,
	)
	if not asset:
		return

	if asset.get("hotel_property") and (not only_if_empty or not doc.get(property_field)):
		doc.set(property_field, asset["hotel_property"])
	if asset.get("hotel_room") and (not only_if_empty or not doc.get(room_field)):
		doc.set(room_field, asset["hotel_room"])


@frappe.whitelist()
def get_branch_hotel_defaults(branch: str | None = None) -> dict[str, str]:
	return get_branch_brand_location(branch)
