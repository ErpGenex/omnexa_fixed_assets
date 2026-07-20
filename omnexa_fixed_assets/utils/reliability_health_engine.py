# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

from dataclasses import dataclass

import frappe
from frappe.utils import flt, get_datetime, now_datetime, nowdate


@dataclass
class ReliabilityMetrics:
	mtbf: float
	mttr: float
	availability: float
	failure_frequency: float
	reliability_score: float
	uptime: float
	downtime: float


def classify_health_status(score: float) -> str:
	s = flt(score)
	if s < 20:
		return "Critical"
	if s < 40:
		return "Poor"
	if s < 60:
		return "Fair"
	if s < 80:
		return "Good"
	return "Excellent"


def compute_health_score(
	condition_score: float,
	reliability_score: float,
	maintenance_score: float,
	cost_efficiency_score: float,
	sensor_stability_score: float,
) -> tuple[float, str]:
	score = (
		flt(condition_score) * 0.35
		+ flt(reliability_score) * 0.25
		+ flt(maintenance_score) * 0.15
		+ flt(cost_efficiency_score) * 0.10
		+ flt(sensor_stability_score) * 0.15
	)
	score = max(0.0, min(100.0, score))
	return score, classify_health_status(score)


def compute_reliability_metrics(asset: str) -> ReliabilityMetrics:
	failures = frappe.get_all(
		"Asset Failure Event",
		filters={"asset": asset
	},
		fields=["event_time", "downtime_hours"],
		order_by="event_time asc",
		limit_page_length=50000,
	)
	total_failures = len(failures)
	total_downtime = sum(flt(x.get("downtime_hours")) for x in failures)
	if total_failures == 0:
		return zero_failure_metrics()
	first_time = get_datetime(failures[0].event_time)
	last_time = get_datetime(failures[-1].event_time)
	observed_hours = max(1.0, (last_time - first_time).total_seconds() / 3600.0)
	return compute_reliability_from_window(total_failures=total_failures, total_downtime=total_downtime, observed_hours=observed_hours)


def zero_failure_metrics() -> ReliabilityMetrics:
	return ReliabilityMetrics(
		mtbf=0.0,
		mttr=0.0,
		availability=100.0,
		failure_frequency=0.0,
		reliability_score=90.0,
		uptime=0.0,
		downtime=0.0,
	)


def compute_reliability_from_window(total_failures: int, total_downtime: float, observed_hours: float) -> ReliabilityMetrics:
	if total_failures <= 0:
		return zero_failure_metrics()
	obs = max(1.0, flt(observed_hours))
	down = max(0.0, flt(total_downtime))
	uptime = max(0.0, obs - down)
	mtbf = uptime / total_failures
	mttr = down / total_failures
	availability = (uptime / (uptime + down) * 100.0) if (uptime + down) > 0 else 100.0
	failure_frequency = total_failures / obs
	reliability_score = max(0.0, min(100.0, availability - (failure_frequency * 100.0)))
	return ReliabilityMetrics(
		mtbf=mtbf,
		mttr=mttr,
		availability=availability,
		failure_frequency=failure_frequency,
		reliability_score=reliability_score,
		uptime=uptime,
		downtime=down,
	)


def recompute_asset_reliability_and_health(asset_name: str) -> dict:
	asset = frappe.get_doc("Fixed Asset", asset_name)
	metrics = compute_reliability_metrics(asset.name)

	condition_score = 100.0 - flt(asset.degradation_index or 0.0)
	maintenance_score = max(0.0, min(100.0, 100.0 - flt(asset.maintenance_burden or 0.0)))
	cost_efficiency_score = max(0.0, min(100.0, flt(asset.repair_efficiency or 0.0)))
	sensor_stability_score = 100.0 if (asset.sensor_state or "Unknown") in ("Online", "Normal") else 60.0
	health_score, health_status = compute_health_score(
		condition_score=condition_score,
		reliability_score=metrics.reliability_score,
		maintenance_score=maintenance_score,
		cost_efficiency_score=cost_efficiency_score,
		sensor_stability_score=sensor_stability_score,
	)

	asset.db_set("mtbf", metrics.mtbf, update_modified=False)
	asset.db_set("mttr", metrics.mttr, update_modified=False)
	asset.db_set("availability", metrics.availability, update_modified=False)
	asset.db_set("failure_frequency", metrics.failure_frequency, update_modified=False)
	asset.db_set("reliability_score", metrics.reliability_score, update_modified=False)
	asset.db_set("uptime", metrics.uptime, update_modified=False)
	asset.db_set("downtime", metrics.downtime, update_modified=False)
	asset.db_set("health_score", health_score, update_modified=False)
	asset.db_set("health_status", health_status, update_modified=False)
	asset.db_set("risk_score", max(0.0, min(100.0, 100.0 - health_score)), update_modified=False)
	asset.db_set("confidence_score", 80.0 if total_meter_readings(asset.name) >= 5 else 50.0, update_modified=False)

	frappe.get_doc(
		{
			"doctype": "Asset Reliability Trend",
			"asset": asset.name,
			"company": asset.company,
			"branch": asset.branch,
			"as_of_date": nowdate(),
			"mtbf": metrics.mtbf,
			"mttr": metrics.mttr,
			"availability": metrics.availability,
			"failure_frequency": metrics.failure_frequency,
			"reliability_score": metrics.reliability_score
	}
	).insert(ignore_permissions=True)

	frappe.get_doc(
		{
			"doctype": "Asset Condition Snapshot",
			"asset": asset.name,
			"company": asset.company,
			"branch": asset.branch,
			"snapshot_time": now_datetime(),
			"condition_state": asset.condition_state or "Unknown",
			"degradation_index": asset.degradation_index,
			"health_score": health_score,
			"health_status": health_status,
			"risk_score": max(0.0, min(100.0, 100.0 - health_score)),
			"confidence_score": asset.confidence_score,
			"source": "scheduler"
	}
	).insert(ignore_permissions=True)

	return {
		"ok": True,
		"asset": asset.name,
		"reliability_score": metrics.reliability_score,
		"health_score": health_score,
		"health_status": health_status
	}


def total_meter_readings(asset_name: str) -> int:
	return frappe.db.count("Asset Meter Reading", {"asset": asset_name
	}) or 0


def run_predictive_rules_for_asset(asset_name: str) -> dict:
	"""Rule-based predictive recommendations (non-ML baseline)."""
	asset = frappe.get_doc("Fixed Asset", asset_name)
	recs = []
	if flt(asset.failure_frequency) > 0.02 and flt(asset.health_score) < 50:
		recs.append(
			{
				"type": "Replace",
				"priority": "High",
				"details": "Failure frequency is rising while health score is declining. Evaluate replacement.",
				"source": "predictive_rules",
				"confidence": 75
	}
		)

	latest_temp = frappe.get_all(
		"Asset Meter Reading",
		filters={"asset": asset.name, "meter_type": "Temperature"
	},
		fields=["value", "reading_time"],
		order_by="reading_time desc",
		limit_page_length=5,
	)
	if len(latest_temp) >= 3:
		values = [flt(x.value) for x in latest_temp]
		if values[0] > values[-1] and (values[0] - values[-1]) >= 5:
			recs.append(
				{
					"type": "Inspect",
					"priority": "Medium",
					"details": "Temperature trend is rising; inspection required.",
					"source": "predictive_rules",
					"confidence": 70
	}
			)

	created = []
	for r in recs:
		doc = frappe.get_doc(
			{
				"doctype": "Asset Recommendation",
				"asset": asset.name,
				"company": asset.company,
				"branch": asset.branch,
				"recommendation_date": nowdate(),
				"type": r["type"],
				"priority": r["priority"],
				"status": "Open",
				"details": r["details"],
				"source": r["source"],
				"confidence": r["confidence"]
	}
		)
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return {"ok": True, "asset": asset.name, "created": created
	}
