# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Rule-based hospitality asset intelligence (not ML — complements core rules)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, get_datetime, now_datetime, nowdate, today


def run_hospitality_intelligence(company: str, branch: str | None = None) -> dict:
	"""Run all intelligence rules; returns summary counts."""
	filters: dict = {"company": company}
	if branch:
		filters["branch"] = branch
	return {
		"missing_asset_predictions": _predict_missing_assets(filters),
		"movement_anomalies": _detect_movement_anomalies(filters),
		"replacement_recommendations": _replacement_predictions(filters),
		"linen_loss_signals": _linen_loss_predictions(filters),
	}


def _predict_missing_assets(filters: dict) -> int:
	threshold_days = int(frappe.conf.get("omnexa_missing_asset_prediction_days") or 7)
	since = add_days(today(), -threshold_days)
	assets = frappe.get_all(
		"Fixed Asset",
		filters={
			**filters,
			"rfid_tag": ["is", "set"],
			"scan_status": ["not in", ["Missing", "Mismatch"]],
		},
		fields=["name", "asset_name", "last_inventory_scan_at"],
		limit=2000,
	)
	created = 0
	for row in assets:
		last = row.last_inventory_scan_at
		if last and get_datetime(last) >= get_datetime(since):
			continue
		msg = _("Asset not seen via RFID for {0}+ days — missing risk.").format(threshold_days)
		if _recommendation_exists(row.name, "Monitor", msg):
			continue
		_create_asset_recommendation(row.name, filters, "Monitor", "High", msg, confidence=72)
		created += 1
	return created


def _detect_movement_anomalies(filters: dict) -> int:
	window_minutes = int(frappe.conf.get("omnexa_movement_anomaly_window_minutes") or 60)
	max_moves = int(frappe.conf.get("omnexa_movement_anomaly_threshold") or 5)
	since = add_to_date(now_datetime(), minutes=-window_minutes)
	rows = frappe.db.sql(
		"""
		select fixed_asset, count(*) as cnt
		from `tabFixed Asset Movement Log`
		where company=%(company)s
		{branch_sql}
		and creation >= %(since)s
		and reference_doctype = 'RFID Scan Log'
		group by fixed_asset
		having cnt >= %(max_moves)s
		""".format(branch_sql="and branch=%(branch)s" if filters.get("branch") else ""),
		{**filters, "since": since, "max_moves": max_moves},
		as_dict=True,
	)
	created = 0
	for row in rows:
		msg = _("Unusual movement: {0} RFID moves in {1} minutes.").format(row.cnt, window_minutes)
		if _recommendation_exists(row.fixed_asset, "Inspect", msg):
			continue
		_create_asset_recommendation(row.fixed_asset, filters, "Inspect", "Critical", msg, confidence=88)
		created += 1
	return created


def _replacement_predictions(filters: dict) -> int:
	assets = frappe.get_all(
		"Fixed Asset",
		filters={**filters, "status": ["not in", ["disposed", "fully_depreciated"]]},
		fields=["name", "asset_name", "health_score", "accumulated_depreciation", "acquisition_cost"],
		limit=2000,
	)
	created = 0
	for row in assets:
		cost = float(row.acquisition_cost or 0)
		acc = float(row.accumulated_depreciation or 0)
		health = float(row.health_score or 100)
		if cost <= 0:
			continue
		nbv_ratio = (cost - acc) / cost
		if nbv_ratio > 0.25 and health >= 40:
			continue
		msg = _("Replacement candidate: low NBV ratio or poor health.")
		if _recommendation_exists(row.name, "Replace", msg):
			continue
		confidence = 65 if nbv_ratio <= 0.25 else 55
		_create_asset_recommendation(row.name, filters, "Replace", "Medium", msg, confidence=confidence)
		created += 1
	return created


def _linen_loss_predictions(filters: dict) -> int:
	if not frappe.db.exists("DocType", "Linen Item"):
		return 0
	threshold = int(frappe.conf.get("omnexa_linen_replacement_threshold") or 15)
	items = frappe.get_all(
		"Linen Item",
		filters={**filters, "status": ["not in", ["Disposed", "Missing"]]},
		fields=["name", "linen_name", "linen_type", "wash_count", "expected_life_cycles"],
		limit=3000,
	)
	created = 0
	for row in items:
		remaining = int(row.expected_life_cycles or 0) - int(row.wash_count or 0)
		if remaining > threshold:
			continue
		msg = _("Linen {0}: {1} wash cycles remaining — plan replacement.").format(row.name, remaining)
		if frappe.db.exists("Linen Shortage Alert", {"message": msg, "status": "Open"}):
			continue
		frappe.get_doc(
			{
				"doctype": "Linen Shortage Alert",
				"company": filters["company"],
				"branch": filters.get("branch"),
				"linen_type": row.linen_type,
				"missing_quantity": 0,
				"message": msg,
				"alert_time": now_datetime(),
				"status": "Open",
				"alert_category": "Replacement Warning",
			}
		).insert(ignore_permissions=True)
		created += 1
	return created


def _recommendation_exists(asset: str, rec_type: str, details: str) -> bool:
	return bool(
		frappe.db.exists(
			"Asset Recommendation",
			{"asset": asset, "type": rec_type, "details": details, "status": "Open"},
		)
	)


def _create_asset_recommendation(
	asset: str, filters: dict, rec_type: str, priority: str, details: str, *, confidence: float
) -> None:
	frappe.get_doc(
		{
			"doctype": "Asset Recommendation",
			"asset": asset,
			"company": filters["company"],
			"branch": filters.get("branch"),
			"recommendation_date": today(),
			"type": rec_type,
			"priority": priority,
			"status": "Open",
			"details": details,
			"source": "hospitality_intelligence",
			"confidence": confidence,
		}
	).insert(ignore_permissions=True)


def log_intelligence_audit(
	company: str,
	event_type: str,
	message: str,
	*,
	branch: str | None = None,
	entity_type: str | None = None,
	entity_name: str | None = None,
	source: str = "System Automation",
	device: str | None = None,
) -> None:
	if not frappe.db.exists("DocType", "Hospitality Audit Event"):
		return
	frappe.get_doc(
		{
			"doctype": "Hospitality Audit Event",
			"company": company,
			"branch": branch,
			"event_time": now_datetime(),
			"event_type": event_type,
			"entity_type": entity_type,
			"entity_name": entity_name,
			"message": message,
			"source": source,
			"device": device,
			"user": frappe.session.user if frappe.session.user != "Guest" else None,
		}
	).insert(ignore_permissions=True)
