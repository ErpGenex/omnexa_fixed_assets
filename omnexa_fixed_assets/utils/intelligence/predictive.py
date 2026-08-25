# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Statistical predictive signals (rule + trend based; complements rules_engine)."""

from __future__ import annotations

import frappe
from frappe.utils import add_days, flt, get_datetime, now_datetime, today


def run_predictive_analytics(company: str, branch: str | None = None) -> dict:
	filters: dict = {"company": company}
	if branch:
		filters["branch"] = branch
	return {
		"missing_asset_risk": _missing_asset_risk_scores(filters),
		"linen_loss_rate": _linen_loss_rate(filters),
		"movement_velocity": _movement_velocity(filters),
		"replacement_forecast_90d": _replacement_forecast(filters, days=90),
	}


def _missing_asset_risk_scores(filters: dict, limit: int = 20) -> list[dict]:
	assets = frappe.get_all(
		"Fixed Asset",
		filters={**filters, "rfid_tag": ["is", "set"]},
		fields=["name", "asset_name", "last_inventory_scan_at", "scan_status", "hotel_property"],
		limit=500,
	)
	out = []
	now = now_datetime()
	for row in assets:
		last = row.last_inventory_scan_at
		days_silent = 999
		if last:
			days_silent = (now - get_datetime(last)).days
		risk = min(95, 20 + days_silent * 8)
		if row.scan_status in ("Missing", "Mismatch"):
			risk = 98
		if risk < 40:
			continue
		out.append(
			{
				"asset": row.name,
				"asset_name": row.asset_name,
				"hotel_property": row.hotel_property,
				"days_since_scan": days_silent if last else None,
				"risk_score": risk,
				"confidence": min(92, 50 + min(days_silent, 10) * 4),
			}
		)
	out.sort(key=lambda x: x["risk_score"], reverse=True)
	return out[:limit]


def _linen_loss_rate(filters: dict) -> dict:
	if not frappe.db.exists("DocType", "Linen Item"):
		return {"rate_pct": 0, "missing": 0, "total": 0}
	total = frappe.db.count("Linen Item", filters) or 1
	missing = frappe.db.count("Linen Item", {**filters, "status": "Missing"})
	shortages = frappe.db.count("Linen Shortage Alert", {**filters, "status": "Open"})
	return {
		"total": total,
		"missing": missing,
		"open_shortages": shortages,
		"rate_pct": round(missing / total * 100, 2),
	}


def _movement_velocity(filters: dict) -> dict:
	since = add_days(today(), -7)
	count = frappe.db.count(
		"Fixed Asset Movement Log",
		{**filters, "creation": [">=", since], "reference_doctype": "RFID Scan Log"},
	)
	return {"rfid_movements_7d": count, "daily_avg": round(count / 7, 1)}


def _replacement_forecast(filters: dict, days: int = 90) -> list[dict]:
	assets = frappe.get_all(
		"Fixed Asset",
		filters={**filters, "status": ["not in", ["disposed"]]},
		fields=["name", "asset_name", "health_score", "acquisition_cost", "accumulated_depreciation"],
		limit=1000,
	)
	out = []
	for row in assets:
		cost = flt(row.acquisition_cost)
		if cost <= 0:
			continue
		nbv_ratio = (cost - flt(row.accumulated_depreciation)) / cost
		health = flt(row.health_score or 100)
		probability = 0
		if nbv_ratio <= 0.2:
			probability += 45
		if health < 40:
			probability += 35
		if nbv_ratio <= 0.1:
			probability += 15
		if probability < 30:
			continue
		out.append(
			{
				"asset": row.name,
				"asset_name": row.asset_name,
				"probability": min(probability, 95),
				"horizon_days": days,
				"confidence": min(88, 40 + probability // 2),
			}
		)
	out.sort(key=lambda x: x["probability"], reverse=True)
	return out[:15]
