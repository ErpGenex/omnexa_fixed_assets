# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Bootstrap hotel asset management structures (feature-flag gated).

NOTE: The Hotel feature is controlled by site config `omnexa_feature_flags.enable_hotel_asset_management`.
This patch is safe to run on all sites; it is a no-op when the flag is disabled.
"""

from __future__ import annotations

import frappe


def execute():
	try:
		from omnexa_fixed_assets.install import (
			ensure_hotel_asset_management_custom_fields,
			ensure_hotel_roles,
			ensure_hotel_report_roles,
			ensure_hotel_workspace_links,
		)

		ensure_hotel_asset_management_custom_fields()
		ensure_hotel_roles()
		ensure_hotel_report_roles()
		ensure_hotel_workspace_links()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "omnexa_fixed_assets: bootstrap_hotel_asset_management")
