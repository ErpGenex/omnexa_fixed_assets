# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Ensure Asset Insurance appears under Fixed Assets (/app/fixed-assets sidebar)."""


def execute() -> None:
	from omnexa_fixed_assets.asset_insurance_workspace import (
		ensure_asset_insurance_on_fixed_assets_workspace,
	)
	from omnexa_fixed_assets.install import _remove_legacy_asset_insurance_workspace_slug

	_remove_legacy_asset_insurance_workspace_slug()
	ensure_asset_insurance_on_fixed_assets_workspace()

	try:
		from omnexa_core.omnexa_core.workspace_control_tower import sync_workspace_for_app

		sync_workspace_for_app("omnexa_fixed_assets")
		sync_workspace_for_app("omnexa_fixed_assets_insurance")
	except Exception:
		import frappe

		frappe.log_error(frappe.get_traceback(), "Omnexa: patch ensure_asset_insurance_sidebar")

	import frappe

	frappe.clear_cache()
