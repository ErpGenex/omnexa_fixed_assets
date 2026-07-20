# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Ensure Fixed Assets script reports are visible on the desk for finance and ops roles."""

import frappe

REPORT_NAMES = (
	"Asset Register Report",
	"Asset Valuation Report",
	"Fixed Asset Summary",
	"Fixed Asset NBV by Category",
	"Asset Depreciation Schedule",
	"Fixed Asset Depreciation Posting Summary",
	"Asset Movement Report",
	"Asset Disposal Report",
	"Asset Maintenance Report",
)

ROLES = (
	"System Manager",
	"Company Admin",
	"Desk User",
	"Report Manager",
	"Accountant",
	"Accounts Manager",
	"Accounts User",
)


def execute():
	valid_roles = set(frappe.get_all("Role", pluck="name"))
	roles = tuple(r for r in ROLES if r in valid_roles)
	if not roles:
		return

	for name in REPORT_NAMES:
		if not frappe.db.exists("Report", name):
			continue
		doc = frappe.get_doc("Report", name)
		doc.roles = []
		for role in roles:
			doc.append("roles", {"role": role})
		doc.save(ignore_permissions=True)

	frappe.clear_cache()
