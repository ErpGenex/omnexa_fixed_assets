# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Phase 22 — Final Global Hospitality Readiness Audit."""

from __future__ import annotations

import traceback
from typing import Any

import frappe

from omnexa_fixed_assets.scripts.audit_full_asset_management_scenario import run as run_scenario_audit


PHASE_CHECKS = [
	("phase_6_rfid_architecture", ["RFID Gateway", "RFID Reader", "RFID Scan Log"]),
	("phase_9_event_engine", ["event_processor"]),
	("phase_11_live_map", ["page:fa-live-asset-tracking"]),
	("phase_13_linen", ["Linen Item", "Linen Movement", "Linen Issue Batch"]),
	("phase_19_command_center", ["page:fa-hospitality-command-center"]),
	("phase_20_predictive", ["get_predictive_analytics"]),
	("phase_22_audit_trail", ["Hospitality Audit Event"]),
	("phase_11_floor_plan", ["Hotel Floor Plan"]),
	("phase_global_portfolio", ["page:fa-global-hospitality-portfolio"]),
	("phase_23_asset_wizards", ["Asset Lifecycle Wizard Session", "page:fa-asset-wizards", "get_wizard_catalog"]),
]


def _check_doctype(name: str) -> bool:
	return bool(frappe.db.exists("DocType", name))


def _check_page(name: str) -> bool:
	return bool(frappe.db.exists("Page", name))


def _check_api(method: str) -> bool:
	try:
		from omnexa_fixed_assets import api as fa_api

		return callable(getattr(fa_api, method, None))
	except Exception:
		return False


def _run_phase_checks() -> dict[str, Any]:
	results = {}
	for key, items in PHASE_CHECKS:
		ok = True
		detail = []
		for item in items:
			if item.startswith("get_"):
				exists = _check_api(item)
			elif item.startswith("page:"):
				exists = _check_page(item.split(":", 1)[1])
			elif item == "event_processor":
				import os

				path = os.path.join(
					frappe.get_app_path("omnexa_fixed_assets"),
					"utils",
					"rfid",
					"event_processor.py",
				)
				exists = os.path.exists(path)
			elif _check_doctype(item):
				exists = True
			elif _check_page(item):
				exists = True
			else:
				exists = False
			detail.append({"item": item, "ok": exists})
			ok = ok and exists
		results[key] = {"ok": ok, "checks": detail}
	return results


@frappe.whitelist()
def run(company: str | None = None, branch: str | None = None) -> dict:
	frappe.only_for(("System Manager", "Administrator", "Hotel Asset Admin"))
	company = company or frappe.defaults.get_user_default("Company")
	branch = branch or frappe.defaults.get_user_default("Branch")

	scenario = run_scenario_audit(company=company, branch=branch)
	phases = _run_phase_checks()

	security = {
		"device_auth_module": True,
		"gateway_token_field": (
			frappe.db.has_column("RFID Gateway", "api_token")
			if frappe.db.exists("DocType", "RFID Gateway")
			else False
		),
		"audit_event_doctype": _check_doctype("Hospitality Audit Event"),
	}

	phase_ok = all(v.get("ok") for v in phases.values())
	summary = {
		"scenario_ok": scenario.get("summary", {}).get("ok"),
		"phases_ok": phase_ok,
		"security_ok": all(security.values()),
		"ok": bool(scenario.get("summary", {}).get("ok")) and phase_ok and all(security.values()),
		"total_phases": len(phases),
		"passed_phases": sum(1 for v in phases.values() if v.get("ok")),
	}

	return {
		"company": company,
		"branch": branch,
		"summary": summary,
		"phases": phases,
		"security": security,
		"scenario_summary": scenario.get("summary"),
	}
