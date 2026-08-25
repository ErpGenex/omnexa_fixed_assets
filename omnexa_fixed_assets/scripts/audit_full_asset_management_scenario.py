# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Full fixed-asset management scenario audit (desk + API + business flows)."""

from __future__ import annotations

import importlib
import traceback
from typing import Any

import frappe
from frappe.utils import add_days, nowdate, today

from omnexa_core.omnexa_core.session_context import set_view_context

from omnexa_fixed_assets.scripts.audit_fixed_assets_desk import run_fixed_assets_desk_audit
from omnexa_fixed_assets.utils.navbar_scope import audit_fixed_assets_navbar_scope


def _step(name: str, fn) -> dict:
	try:
		out = fn()
		ok = bool(out.get("ok", True)) if isinstance(out, dict) else bool(out)
		return {"ok": ok, **(out if isinstance(out, dict) else {"detail": out})}
	except Exception as exc:
		return {"ok": False, "error": str(exc), "trace": traceback.format_exc()[-800:]}


def _navbar_scope_on_doctypes() -> dict:
	audit = audit_fixed_assets_navbar_scope()
	return {"ok": audit.get("ok"), "issues": audit.get("issues", [])}


def _master_data_counts(company: str, branch: str | None) -> dict:
	filters = {"company": company}
	if branch:
		filters["branch"] = branch
	counts = {
		"fixed_asset_categories": frappe.db.count("Fixed Asset Category", filters),
		"fixed_assets": frappe.db.count("Fixed Asset", filters),
		"hotel_properties": frappe.db.count("Hotel Property", filters),
		"hotel_rooms": frappe.db.count("Hotel Room", filters),
		"hotel_transfers": frappe.db.count("Hotel Asset Transfer", filters),
		"hotel_inspections": frappe.db.count("Hotel Asset Inspection", filters),
		"rfid_scan_logs": frappe.db.count("RFID Scan Log", filters),
		"depreciation_entries": frappe.db.count(
			"Fixed Asset Depreciation Entry", {"company": company, "docstatus": 1}
		),
	}
	return {"ok": counts["fixed_assets"] > 0, "counts": counts}


def _navbar_defaults_on_new_docs(company: str, branch: str) -> dict:
	from omnexa_core.omnexa_core.user_context import apply_company_branch_defaults

	set_view_context(company=company, branch=branch, view_all_branches=0)
	checks = {}
	for dt in (
		"Fixed Asset",
		"Hotel Property",
		"Hotel Asset Transfer",
		"Fixed Asset Acquisition",
		"Fixed Asset Depreciation Entry",
	):
		if not frappe.db.exists("DocType", dt):
			checks[dt] = {"ok": False, "error": "missing doctype"}
			continue
		doc = frappe.new_doc(dt)
		apply_company_branch_defaults(doc)
		checks[dt] = {
			"ok": doc.get("company") == company and doc.get("branch") == branch,
			"company": doc.get("company"),
			"branch": doc.get("branch"),
		}
	return {"ok": all(v.get("ok") for v in checks.values()), "checks": checks}


def _hotel_property_brand_location(company: str, branch: str) -> dict:
	from omnexa_fixed_assets.utils.hotel_field_defaults import apply_hotel_property_branch_defaults

	doc = frappe.new_doc("Hotel Property")
	doc.company = company
	doc.branch = branch
	doc.property_name = f"Audit Property {frappe.generate_hash(length=6)}"
	apply_hotel_property_branch_defaults(doc)
	return {
		"ok": bool((doc.brand or "").strip()) and bool((doc.location or "").strip()),
		"brand": doc.brand,
		"location": doc.location,
	}


def _asset_transfer_from_fixed_asset(company: str, branch: str) -> dict:
	asset = frappe.get_all(
		"Fixed Asset",
		filters={"company": company, "branch": branch},
		fields=["name", "hotel_property", "hotel_room"],
		limit=1,
	)
	if not asset:
		asset = frappe.get_all(
			"Fixed Asset",
			filters={"company": company},
			fields=["name", "hotel_property", "hotel_room"],
			limit=1,
		)
	if not asset:
		return {"ok": False, "error": "no fixed asset for company"}
	row = asset[0]
	doc = frappe.new_doc("Hotel Asset Transfer")
	doc.company = company
	doc.branch = branch
	doc.posting_date = today()
	doc.fixed_asset = row.name
	from omnexa_fixed_assets.utils.hotel_field_defaults import sync_hotel_fields_from_fixed_asset

	sync_hotel_fields_from_fixed_asset(
		doc, property_field="from_hotel_property", room_field="from_hotel_room"
	)
	return {
		"ok": bool(doc.from_hotel_property) or bool(row.hotel_property),
		"asset": row.name,
		"from_property": doc.from_hotel_property,
		"from_room": doc.from_hotel_room,
	}


def _api_smoke(company: str, branch: str | None) -> dict:
	from omnexa_fixed_assets import api as fa_api

	asset = frappe.get_all("Fixed Asset", filters={"company": company}, pluck="name", limit=1)
	asset_name = asset[0] if asset else None
	results: dict[str, Any] = {}

	results["get_eam_feature_flags"] = _step(
		"flags", lambda: {"ok": bool(fa_api.get_eam_feature_flags())}
	)
	results["get_hotel_assets_portal_context"] = _step(
		"portal",
		lambda: {
			"ok": bool(
				(fa_api.get_hotel_assets_portal_context(company=company, branch=branch) or {}).get("ok")
			)
		},
	)
	results["get_asset_command_center"] = _step(
		"command_center",
		lambda: {"ok": bool(fa_api.get_asset_command_center(company=company, branch=branch))},
	)
	results["get_scheduler_board_payload"] = _step(
		"scheduler",
		lambda: {"ok": bool(fa_api.get_scheduler_board_payload(company=company, branch=branch))},
	)
	if asset_name:
		results["get_asset_health_payload"] = _step(
			"health",
			lambda: {"ok": bool(fa_api.get_asset_health_payload(asset_name))},
		)
		results["locate_asset"] = _step(
			"locate",
			lambda: {"ok": bool(fa_api.locate_asset(asset_name))},
		)
		results["get_live_rfid_movements"] = _step(
			"live_movements",
			lambda: {"ok": bool(fa_api.get_live_rfid_movements(company=company, branch=branch))},
		)
		results["get_live_asset_map"] = _step(
			"live_map",
			lambda: {"ok": bool(fa_api.get_live_asset_map(company=company, branch=branch))},
		)
		results["get_linen_dashboard"] = _step(
			"linen_dashboard",
			lambda: {"ok": bool(fa_api.get_linen_dashboard(company=company, branch=branch))},
		)
		results["get_asset_heatmap"] = _step(
			"heatmap",
			lambda: {"ok": bool(fa_api.get_asset_heatmap(company=company, branch=branch))},
		)
		results["run_hospitality_intelligence"] = _step(
			"intelligence",
			lambda: {"ok": bool(fa_api.run_hospitality_intelligence(company=company, branch=branch))},
		)
		results["get_global_hospitality_portfolio"] = _step(
			"global_portfolio",
			lambda: {"ok": bool(fa_api.get_global_hospitality_portfolio(company=company))},
		)
		results["get_predictive_analytics"] = _step(
			"predictive",
			lambda: {"ok": bool(fa_api.get_predictive_analytics(company=company, branch=branch))},
		)
		results["get_wizard_catalog"] = _step(
			"wizard_catalog",
			lambda: {
				"ok": bool(
					(fa_api.get_wizard_catalog() or {}).get("ok")
					and len((fa_api.get_wizard_catalog() or {}).get("wizards") or []) >= 10
				)
			},
		)
		results["list_wizard_drafts"] = _step(
			"wizard_drafts",
			lambda: {"ok": bool((fa_api.list_wizard_drafts(company=company) or {}).get("ok"))},
		)
		results["get_asset_lifecycle_timeline"] = _step(
			"lifecycle",
			lambda: {"ok": bool(fa_api.get_asset_lifecycle_timeline(asset_name))},
		)
		results["get_qr_svg_data_uri"] = _step(
			"qr",
			lambda: {"ok": bool(fa_api.get_qr_svg_data_uri(asset_name))},
		)
	ok = all(v.get("ok") for v in results.values())
	return {"ok": ok, "apis": results}


def _report_navbar_coverage() -> dict:
	reports = frappe.get_all(
		"Report",
		filters={"module": "Omnexa Fixed Assets", "report_type": "Script Report", "disabled": 0},
		pluck="name",
	)
	missing = []
	for name in reports:
		scrub = frappe.scrub(name)
		path = f"omnexa_fixed_assets.omnexa_fixed_assets.report.{scrub}.{scrub}"
		try:
			mod = importlib.import_module(path)
			src = mod.__file__
		except Exception:
			continue
		if not src:
			continue
		with open(src, encoding="utf-8") as fh:
			body = fh.read()
			if "merge_navbar_report_filters" not in body:
				missing.append(name)
	return {"ok": not missing, "total": len(reports), "missing_navbar_merge": missing}


def _workspace_and_pages() -> dict:
	ws_ok = frappe.db.exists("Workspace", "Fixed Assets")
	pages = [
		"fa-hotel-assets-dashboard",
		"fa-executive-dashboard",
		"fa-asset-scan-pwa",
		"fa-live-asset-tracking",
		"fa-linen-dashboard",
		"fa-hospitality-command-center",
		"fa-global-hospitality-portfolio",
		"fa-asset-wizards",
		"fixed-assets-workcenter",
		"fixed-assets-analytics-dashboard",
		"fixed-assets-operations-desk",
		"fixed-assets-finance-desk",
		"fixed-assets-customer-portal",
	]
	page_status = {p: bool(frappe.db.exists("Page", p)) for p in pages}
	return {"ok": bool(ws_ok) and all(page_status.values()), "workspace": ws_ok, "pages": page_status}


def _ias16_depreciation_smoke(company: str) -> dict:
	"""Validate depreciation batch API returns structured result without submitting."""
	from omnexa_fixed_assets import api as fa_api

	try:
		out = fa_api.run_monthly_depreciation_batch(company=company, submit_entries=0, limit=5)
		return {"ok": isinstance(out, dict), "keys": sorted(out.keys()) if isinstance(out, dict) else []}
	except Exception as exc:
		return {"ok": False, "error": str(exc)}


@frappe.whitelist()
def run_full_asset_management_audit(
	company: str | None = None, branch: str | None = None
) -> dict:
	"""End-to-end audit for fixed-asset management on the current site."""
	frappe.only_for(("System Manager", "Administrator", "Hotel Asset Admin"))
	if not company:
		company = (
			frappe.defaults.get_user_default("omnexa_view_company")
			or frappe.db.get_single_value("Global Defaults", "default_company")
		)
	if not branch and company:
		branch = frappe.db.get_value(
			"Branch", {"company": company, "is_head_office": 1}, "name"
		) or frappe.db.get_value("Branch", {"company": company}, "name")

	if company:
		try:
			set_view_context(
				company=company,
				branch=branch,
				view_all_branches=0 if branch else 1,
			)
		except Exception:
			pass

	scenarios = {
		"navbar_scope_fields": _step("navbar_scope", _navbar_scope_on_doctypes),
		"navbar_defaults_new_docs": _step(
			"navbar_defaults",
			lambda: _navbar_defaults_on_new_docs(company, branch) if branch else {"ok": False, "error": "no branch"},
		),
		"master_data": _step("master_data", lambda: _master_data_counts(company, branch)),
		"hotel_brand_location": _step(
			"hotel_brand",
			lambda: _hotel_property_brand_location(company, branch) if branch else {"ok": False},
		),
		"hotel_transfer_autofill": _step(
			"hotel_transfer",
			lambda: _asset_transfer_from_fixed_asset(company, branch) if branch else {"ok": False},
		),
		"workspace_pages": _step("workspace", _workspace_and_pages),
		"report_navbar_coverage": _step("report_navbar", _report_navbar_coverage),
		"api_smoke": _step("api", lambda: _api_smoke(company, branch)),
		"ias16_depreciation": _step("ias16", lambda: _ias16_depreciation_smoke(company)),
	}

	desk = run_fixed_assets_desk_audit(company=company, branch=branch)
	scenarios["desk_audit"] = {
		"ok": desk.get("summary", {}).get("fail", 1) == 0,
		"summary": desk.get("summary"),
		"portal": desk.get("portal"),
		"report_failures": [
			k for k, v in (desk.get("reports") or {}).items() if not v.get("ok")
		],
	}

	passed = sum(1 for v in scenarios.values() if v.get("ok"))
	failed = [k for k, v in scenarios.items() if not v.get("ok")]

	return {
		"company": company,
		"branch": branch,
		"scenarios": scenarios,
		"desk": desk,
		"summary": {
			"total": len(scenarios),
			"passed": passed,
			"failed": len(failed),
			"failed_keys": failed,
			"ok": not failed and desk.get("summary", {}).get("fail", 0) == 0,
		},
	}


def run(company: str | None = None, branch: str | None = None):
	frappe.set_user("Administrator")
	return run_full_asset_management_audit(company=company, branch=branch)
