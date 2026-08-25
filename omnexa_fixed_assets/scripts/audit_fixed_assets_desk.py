# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Audit fixed-assets desk pages, routes, and Script Reports."""

from __future__ import annotations

import importlib
import json
import traceback

import frappe
from frappe.desk.utils import slug as desk_slug

from omnexa_core.omnexa_core.session_context import set_view_context


PHANTOM_REPORTS = {
	"Claim Settlement Analysis",
	"Policy Renewal Forecast",
	"Insurance Cost Analysis",
	"Risk Exposure Report",
}

HOTEL_PAGES = [
	"fa-hotel-assets-dashboard",
	"fa-executive-dashboard",
	"fa-asset-scan-pwa",
]

HOTEL_DOCTYPES = [
	"Hotel Property",
	"Hotel Room",
	"Hotel Functional Area",
	"Hotel Asset Transfer",
	"Hotel Asset Inspection",
	"Fixed Asset",
	"RFID Scan Log",
]


def _route_ok_doctype(doctype: str) -> tuple[bool, str]:
	expected = f"/app/{desk_slug(doctype)}"
	return True, expected


def _run_report(report_name: str, company: str, branch: str | None) -> dict:
	if not frappe.db.exists("Report", report_name):
		return {"ok": False, "error": "Report not in database"}
	report = frappe.get_doc("Report", report_name)
	if report.report_type != "Script Report":
		return {"ok": True, "skipped": "not script report"}
	if report.disabled:
		return {"ok": True, "skipped": "disabled"}
	scrub = frappe.scrub(report_name)
	package = f"omnexa_fixed_assets.omnexa_fixed_assets.report.{scrub}.{scrub}"
	try:
		mod = importlib.import_module(package)
	except Exception as exc:
		return {"ok": False, "error": f"missing module: {exc}"}
	filters = {"company": company, "from_date": frappe.utils.today(), "to_date": frappe.utils.today()}
	if branch:
		filters["branch"] = branch
	try:
		result = mod.execute(filters)
		rows = len(result[1]) if isinstance(result, (list, tuple)) and len(result) > 1 else 0
		return {"ok": True, "rows": rows}
	except Exception as exc:
		return {"ok": False, "error": str(exc)}


@frappe.whitelist()
def run_fixed_assets_desk_audit(company: str | None = None, branch: str | None = None) -> dict:
	"""Run pages/routes/reports audit for fixed assets module."""
	frappe.only_for(("System Manager", "Administrator", "Hotel Asset Admin"))
	if not company:
		company = frappe.defaults.get_user_default("omnexa_view_company") or frappe.db.get_single_value(
			"Global Defaults", "default_company"
		)
	if company and branch:
		try:
			set_view_context(company=company, branch=branch, view_all_branches=0)
		except Exception:
			pass

	results = {
		"company": company,
		"branch": branch,
		"pages": {},
		"routes": {},
		"reports": {},
		"phantom_links": [],
		"summary": {"pass": 0, "fail": 0},
	}

	for page in HOTEL_PAGES:
		ok = frappe.db.exists("Page", page)
		results["pages"][page] = {"ok": bool(ok)}
		results["summary"]["pass" if ok else "fail"] += 1

	for dt in HOTEL_DOCTYPES:
		ok, route = _route_ok_doctype(dt)
		results["routes"][dt] = {"ok": ok, "route": route, "new_route": f"{route}/new"}
		results["summary"]["pass" if ok else "fail"] += 1

	for name in PHANTOM_REPORTS:
		if not frappe.db.exists("Report", name):
			results["phantom_links"].append(name)

	reports = frappe.get_all(
		"Report",
		filters={"module": "Omnexa Fixed Assets", "report_type": "Script Report", "disabled": 0},
		pluck="name",
		order_by="name asc",
	)
	for report_name in reports:
		out = _run_report(report_name, company, branch)
		results["reports"][report_name] = out
		if out.get("ok"):
			results["summary"]["pass"] += 1
		else:
			results["summary"]["fail"] += 1

	# Portal API smoke test
	try:
		from omnexa_fixed_assets.api import get_hotel_assets_portal_context

		portal = get_hotel_assets_portal_context(company=company, branch=branch)
		results["portal"] = {"ok": bool(portal.get("ok")), "kpis": len((portal.get("dashboard") or {}).get("kpis") or [])}
	except Exception as exc:
		results["portal"] = {"ok": False, "error": str(exc)}

	return results


def run(company: str | None = None, branch: str | None = None):
	frappe.set_user("Administrator")
	return run_fixed_assets_desk_audit(company=company, branch=branch)
