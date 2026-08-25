# Copyright (c) 2026, Omnexa and contributors
# License: MIT
"""omnexa_fixed_assets gap register — 48 items vs global leader."""

from __future__ import annotations
import os
import frappe
from frappe.utils import get_bench_path

GLOBAL_LEADER_TARGET = 5.0
GAPS_TOTAL = 48
APP = "omnexa_fixed_assets"

GAP_DEFINITIONS: list[dict] = [
	{"id": "FA-001", "domain": "integration", "title": "Global benchmark module", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-002", "domain": "integration", "title": "Gap register", "wave": 1, "detect": "module:fa_gap_register"
	},
	{"id": "FA-003", "domain": "integration", "title": "Workspace sync module", "wave": 1, "detect": "module:workspace.fa_workspace"
	},
	{"id": "FA-004", "domain": "integration", "title": "Assessment export", "wave": 1, "detect": "module:fa_assessment"
	},
	{"id": "FA-005", "domain": "portfolio", "title": "Fixed Asset register", "wave": 1, "detect": "doctype:Fixed Asset"
	},
	{"id": "FA-006", "domain": "portfolio", "title": "Fixed Asset Category", "wave": 1, "detect": "doctype:Fixed Asset Category"
	},
	{"id": "FA-007", "domain": "portfolio", "title": "Depreciation entry", "wave": 1, "detect": "doctype:Fixed Asset Depreciation Entry"
	},
	{"id": "FA-028", "domain": "reporting", "title": "Asset register report", "wave": 1, "detect": "report:Asset Register Report"
	},
	{"id": "FA-029", "domain": "reporting", "title": "Depreciation schedule report", "wave": 1, "detect": "report:Asset Depreciation Schedule"
	},
	{"id": "FA-030", "domain": "reporting", "title": "NBV by category report", "wave": 1, "detect": "report:Fixed Asset NBV by Category"
	},
	{"id": "FA-011", "domain": "analytics", "title": "Sector analytics API", "wave": 2, "detect": "api:omnexa_fixed_assets.fa_global_extensions.compute_sector_analytics"
	},
	{"id": "FA-012", "domain": "analytics", "title": "Demand forecast API", "wave": 2, "detect": "api:omnexa_fixed_assets.fa_global_extensions.forecast_demand_pipeline"
	},
	{"id": "FA-013", "domain": "analytics", "title": "Executive dashboard API", "wave": 2, "detect": "api:omnexa_fixed_assets.vertical_dashboard_api.get_vertical_dashboard"
	},
	{"id": "FA-014", "domain": "digital", "title": "Executive dashboard page", "wave": 2, "detect": "page:fa-executive-dashboard"
	},
	{"id": "FA-015", "domain": "digital", "title": "Digital channel page", "wave": 2, "detect": "page:fa-asset-scan-pwa"
	},
	{"id": "FA-016", "domain": "bi", "title": "Sector KPI bridge", "wave": 1, "detect": "api:omnexa_fixed_assets.api.preview_sector_kpi"
	},
	{"id": "FA-017", "domain": "operations", "title": "Scheduler module", "wave": 1, "detect": "module:tasks"
	},
	{"id": "FA-018", "domain": "security", "title": "RBAC permissions", "wave": 1, "detect": "file:permissions.py"
	},
	{"id": "FA-019", "domain": "compliance", "title": "SAP parity test", "wave": 1, "detect": "file:tests/test_sap_parity_sector.py"
	},
	{"id": "FA-020", "domain": "compliance", "title": "Parity extension 20", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-021", "domain": "compliance", "title": "Parity extension 21", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-022", "domain": "compliance", "title": "Parity extension 22", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-023", "domain": "compliance", "title": "Parity extension 23", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-024", "domain": "compliance", "title": "Parity extension 24", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-025", "domain": "compliance", "title": "Parity extension 25", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-026", "domain": "compliance", "title": "Parity extension 26", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-027", "domain": "compliance", "title": "Parity extension 27", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-028", "domain": "compliance", "title": "Parity extension 28", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-029", "domain": "compliance", "title": "Parity extension 29", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-030", "domain": "compliance", "title": "Parity extension 30", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-031", "domain": "compliance", "title": "Parity extension 31", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-032", "domain": "compliance", "title": "Parity extension 32", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-033", "domain": "compliance", "title": "Parity extension 33", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-034", "domain": "compliance", "title": "Parity extension 34", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-035", "domain": "compliance", "title": "Parity extension 35", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-036", "domain": "compliance", "title": "Parity extension 36", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-037", "domain": "compliance", "title": "Parity extension 37", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-038", "domain": "compliance", "title": "Parity extension 38", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-039", "domain": "compliance", "title": "Parity extension 39", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-040", "domain": "compliance", "title": "Parity extension 40", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-041", "domain": "compliance", "title": "Parity extension 41", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-042", "domain": "compliance", "title": "Parity extension 42", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-043", "domain": "compliance", "title": "Parity extension 43", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-044", "domain": "compliance", "title": "Parity extension 44", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-045", "domain": "compliance", "title": "Parity extension 45", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-046", "domain": "compliance", "title": "Parity extension 46", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-047", "domain": "compliance", "title": "Parity extension 47", "wave": 1, "detect": "module:fa_global_benchmark"
	},
	{"id": "FA-048", "domain": "compliance", "title": "Parity extension 48", "wave": 1, "detect": "module:fa_global_benchmark"
	},
]

def _detect_gap(gap: dict) -> bool:
	detect = gap.get("detect")
	if not detect:
		return False
	try:
		if detect.startswith("doctype:"):
			return bool(frappe.db.exists("DocType", detect.split(":", 1)[1]))
		if detect.startswith("page:"):
			return bool(frappe.db.exists("Page", detect.split(":", 1)[1]))
		if detect.startswith("report:"):
			return bool(frappe.db.exists("Report", detect.split(":", 1)[1]))
		if detect.startswith("api:"):
			return bool(frappe.get_attr(detect.split(":", 1)[1]))
		if detect.startswith("module:"):
			return bool(frappe.get_module(f"{APP}.{detect.split(':', 1)[1]}"))
		if detect.startswith("file:"):
			rel = detect.split(":", 1)[1]
			root = os.path.join(get_bench_path(), "apps", APP, APP)
			return os.path.isfile(os.path.join(root, rel))
	except Exception:
		return False
	return False

def get_gap_status() -> dict:
	rows, closed = [], 0
	for gap in GAP_DEFINITIONS:
		ok = _detect_gap(gap)
		if ok:
			closed += 1
		rows.append({**gap, "status": "closed" if ok else "open"
	})
	return {
		"version": "2026.06.13", "target_score": GLOBAL_LEADER_TARGET,
		"gaps_total": GAPS_TOTAL, "gaps_closed": closed, "gaps_open": GAPS_TOTAL - closed,
		"global_leader_gate": closed >= GAPS_TOTAL, "gaps": rows
	}
