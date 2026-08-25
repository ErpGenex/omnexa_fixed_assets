# Copyright (c) 2026, Omnexa and contributors
# License: MIT
import frappe

from omnexa_core.omnexa_core.vertical_dashboard import build_vertical_dashboard_payload


@frappe.whitelist()
def get_vertical_dashboard(company: str | None = None) -> dict:
	return build_vertical_dashboard_payload("omnexa_fixed_assets", company=company)
