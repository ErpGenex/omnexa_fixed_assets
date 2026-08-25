# Copyright (c) 2026, Omnexa and contributors
# License: MIT
import frappe

from omnexa_core.omnexa_core.world_class import certify_app


@frappe.whitelist()
def get_world_class_certification() -> dict:
	return certify_app("omnexa_fixed_assets")
