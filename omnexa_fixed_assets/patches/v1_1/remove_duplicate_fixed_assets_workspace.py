# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Remove stray Workspace created when control-tower key did not match fixture `name`.

Fixture uses `name`: Fixed Assets; registry previously targeted `Fixed assets`, so some sites
ended up with two public workspaces. Keep the fixture document; drop the duplicate.
"""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.exists("Workspace", "Fixed assets"):
		return
	if not frappe.db.exists("Workspace", "Fixed Assets"):
		return
	try:
		frappe.delete_doc("Workspace", "Fixed assets", force=True, ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "omnexa_fixed_assets: remove_duplicate_fixed_assets_workspace")
