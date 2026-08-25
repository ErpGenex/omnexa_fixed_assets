# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe

from omnexa_core.omnexa_core.navbar_scope_fields import ensure_navbar_scope_fields_hidden


def ensure_fixed_assets_navbar_scope_fields() -> dict:
	"""Hide company/branch on all Omnexa Fixed Assets DocTypes; scope comes from desk navbar."""
	updated = 0
	touched: set[str] = set()
	doctypes = frappe.get_all(
		"DocType",
		filters={"module": "Omnexa Fixed Assets"},
		pluck="name",
	)
	for doctype in doctypes:
		meta = frappe.get_meta(doctype)
		has_scope = any(meta.has_field(fn) for fn in ("company", "branch"))
		if not has_scope:
			continue
		touched.add(doctype)

	result = ensure_navbar_scope_fields_hidden()
	return {
		"fixed_assets_doctypes": len(doctypes),
		"fixed_assets_with_scope_fields": len(touched),
		**result,
	}


def audit_fixed_assets_navbar_scope() -> dict:
	"""Return DocTypes whose company/branch fields are still visible on desk."""
	issues: list[str] = []
	doctypes = frappe.get_all(
		"DocType",
		filters={"module": "Omnexa Fixed Assets"},
		pluck="name",
	)
	for doctype in sorted(doctypes):
		meta = frappe.get_meta(doctype)
		for fn in ("company", "branch"):
			if not meta.has_field(fn):
				continue
			df = meta.get_field(fn)
			if not df.hidden or not df.read_only:
				issues.append(
					f"{doctype}.{fn} hidden={int(bool(df.hidden))} read_only={int(bool(df.read_only))}"
				)
	return {
		"doctypes_checked": len(doctypes),
		"issues": issues,
		"ok": not issues,
	}
