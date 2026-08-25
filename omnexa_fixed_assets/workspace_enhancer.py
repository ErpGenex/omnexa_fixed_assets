# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Sync Fixed Assets + Asset Insurance desks via omnexa_core control tower."""

from __future__ import annotations

import frappe


def after_migrate() -> None:
	try:
		from omnexa_core.omnexa_core.workspace_control_tower import (
			_ensure_asset_insurance_workspace,
			sync_workspace_for_app,
		)

		sync_workspace_for_app("omnexa_fixed_assets")
		if frappe.db.exists("DocType", "Insurance Policy"):
			sync_workspace_for_app("omnexa_fixed_assets_insurance")
		_ensure_asset_insurance_workspace()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "omnexa_fixed_assets: workspace_enhancer")

	try:
		from omnexa_fixed_assets.asset_insurance_workspace import (
			bootstrap_asset_insurance_desk,
			ensure_asset_insurance_on_fixed_assets_workspace,
		)

		bootstrap_asset_insurance_desk()
		ensure_asset_insurance_on_fixed_assets_workspace()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "omnexa_fixed_assets: asset insurance sidebar")

	try:
		from omnexa_fixed_assets.install import ensure_fixed_assets_workspace_menus

		ensure_fixed_assets_workspace_menus()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "omnexa_fixed_assets: workspace menus sync")
