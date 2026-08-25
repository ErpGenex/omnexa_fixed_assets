# Copyright (c) 2026, Omnexa and contributors
# MIT License

"""Configurable asset health formula weights."""

from __future__ import annotations

import frappe
from frappe.utils import flt

DEFAULT_WEIGHTS = {
	"weight_condition": 0.35,
	"weight_reliability": 0.25,
	"weight_maintenance": 0.15,
	"weight_cost_efficiency": 0.10,
	"weight_sensor": 0.15,
	"weight_age": 0.0,
	"weight_inspection": 0.0,
	"weight_criticality": 0.0,
}

CONDITION_DEGRADATION = {
	"Normal": 0.0,
	"Watch": 25.0,
	"Alert": 60.0,
	"Critical": 90.0,
	"Unknown": 10.0,
}

CRITICALITY_SCORE = {
	"Low": 100.0,
	"Medium": 85.0,
	"High": 65.0,
	"Safety Critical": 40.0,
}


def get_health_weights() -> dict[str, float]:
	if frappe.db.exists("DocType", "Asset Health Formula Settings"):
		try:
			settings = frappe.get_single("Asset Health Formula Settings")
			weights = {}
			for key in DEFAULT_WEIGHTS:
				weights[key] = flt(getattr(settings, key, None) or DEFAULT_WEIGHTS[key])
			total = sum(weights.values()) or 1.0
			return {k: v / total for k, v in weights.items()}
		except Exception:
			pass
	return DEFAULT_WEIGHTS.copy()


def degradation_from_condition_state(condition_state: str | None) -> float:
	return CONDITION_DEGRADATION.get((condition_state or "Unknown").strip(), 10.0)


def criticality_score(criticality: str | None) -> float:
	return CRITICALITY_SCORE.get((criticality or "Medium").strip(), 85.0)
