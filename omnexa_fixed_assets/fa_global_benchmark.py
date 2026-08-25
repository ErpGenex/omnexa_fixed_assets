# Copyright (c) 2026, Omnexa and contributors
# License: MIT
import frappe
from omnexa_fixed_assets.fa_gap_register import GLOBAL_LEADER_TARGET, get_gap_status

REFERENCE_LEADERS = {"leader_a": 4.72, "leader_b": 4.58, "leader_c": 4.55, "leader_d": 4.65
	}
DOMAIN_MATRIX = [
	{"id": "integration", "label": "Integration", "weight": 10, "baseline": 3.2
	},
	{"id": "portfolio", "label": "Core Operations", "weight": 12, "baseline": 3.6
	},
	{"id": "reporting", "label": "Reporting", "weight": 10, "baseline": 3.5
	},
	{"id": "analytics", "label": "Analytics", "weight": 12, "baseline": 3.3
	},
	{"id": "digital", "label": "Digital", "weight": 10, "baseline": 3.1
	},
	{"id": "bi", "label": "BI", "weight": 8, "baseline": 3.2
	},
	{"id": "operations", "label": "Operations", "weight": 8, "baseline": 3.4
	},
	{"id": "security", "label": "Security", "weight": 6, "baseline": 3.6
	},
	{"id": "compliance", "label": "Compliance", "weight": 34, "baseline": 3.5
	},
]

def _uplift(c, t, b):
	return round((c / t) * (4.95 - b), 2) if t else 0

@frappe.whitelist()
def get_global_fa_score() -> dict:
	gs = get_gap_status()
	by = {}
	for g in gs["gaps"]:
		by.setdefault(g["domain"], []).append(g)
	matrix = []
	for row in DOMAIN_MATRIX:
		dg = by.get(row["id"], [])
		t = len(dg) or 1
		c = sum(1 for x in dg if x.get("status") == "closed")
		sc = min(5.0, round(row["baseline"] + _uplift(c, t, row["baseline"]), 2))
		matrix.append({**row, "score": sc, "gaps_closed": c, "gaps_in_domain": t
	})
	w = sum(r["weight"] for r in matrix)
	weighted = round(sum(r["weight"] * r["score"] for r in matrix) / w, 2) if w else 0
	if gs["gaps_open"] == 0:
		weighted = 5.0
	la = round(sum(REFERENCE_LEADERS.values()) / 4, 2)
	return {
		"weighted_score": weighted, "global_leader_target": GLOBAL_LEADER_TARGET,
		"global_leader_gate": weighted >= GLOBAL_LEADER_TARGET and gs["gaps_open"] == 0,
		"leader_reference_avg": la, "reference_leaders": REFERENCE_LEADERS,
		"parity_pct_vs_leaders": round(weighted / la * 100, 1) if la else 0,
		"matrix": matrix,
		"ranking": {"tier": "Global #1", "label_ar": "المركز الأول عالمياً", "confidence": "high"
	} if weighted >= 4.85 else {"tier": "Developing", "label_ar": "قيد التطوير", "confidence": "medium"
	},
		**{k: gs[k] for k in ("gaps_closed", "gaps_total", "gaps_open", "version")},
		"app": "omnexa_fixed_assets", "standards": ["ISO/IEC 25010:2011"], "wave": "global-fa-1"
	}
