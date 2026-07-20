# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

from __future__ import annotations

import frappe
from frappe.utils import add_months, get_datetime, get_last_day, getdate, nowdate

from omnexa_fixed_assets.api import run_monthly_depreciation_batch
from omnexa_fixed_assets.utils.feature_flags import (
	is_condition_monitoring_enabled,
	is_health_engine_enabled,
	is_predictive_rules_enabled,
	is_reliability_enabled,
	is_scheduler_enabled,
	site_has_any_hotel_assets_company,
)
from omnexa_fixed_assets.utils.reliability_health_engine import (
	recompute_asset_reliability_and_health,
	run_predictive_rules_for_asset,
)


def _resolve_target_posting_date(run_date=None):
	"""Prefer month-end of run month, otherwise previous month-end."""
	rd = getdate(run_date or nowdate())
	if rd == get_last_day(rd):
		return rd
	return get_last_day(add_months(rd, -1))


def run_month_end_depreciation_jobs(posting_date=None):
	"""Scheduled monthly runner for company-specific auto depreciation policies."""
	if not is_scheduler_enabled():
		return
	target_date = getdate(posting_date) if posting_date else _resolve_target_posting_date()
	policies = frappe.get_all(
		"Fixed Asset Auto Depreciation Policy",
		filters={"enabled": 1},
		fields=["name", "company", "branch", "submit_entries", "max_assets_per_run"],
	)

	for p in policies:
		try:
			result = run_monthly_depreciation_batch(
				company=p.company,
				branch=p.branch,
				posting_date=str(target_date),
				submit_entries=1 if p.submit_entries else 0,
				limit=p.max_assets_per_run or 500,
			)
			status = "Success" if result.get("created_count") else "No Data"
			message = (
				f"created={result.get('created_count', 0)}, "
				f"submitted={result.get('submitted_count', 0)}, "
				f"skipped={result.get('skipped_count', 0)}"
			)
			frappe.db.set_value(
				"Fixed Asset Auto Depreciation Policy",
				p.name,
				{
					"last_target_posting_date": str(target_date),
					"last_run_at": get_datetime(),
					"last_run_status": status,
					"last_run_message": message,
				},
				update_modified=False,
			)
		except Exception:
			frappe.log_error(
				title=f"Auto depreciation failed: {p.name}",
				message=frappe.get_traceback(),
			)
			frappe.db.set_value(
				"Fixed Asset Auto Depreciation Policy",
				p.name,
				{
					"last_target_posting_date": str(target_date),
					"last_run_at": get_datetime(),
					"last_run_status": "Failed",
					"last_run_message": "See Error Log for traceback.",
				},
				update_modified=False,
			)


def run_daily_reliability_jobs():
	"""Daily refresh of reliability and health metrics for monitored assets."""
	if not is_scheduler_enabled():
		return
	if not is_reliability_enabled() and not is_health_engine_enabled():
		return
	assets = frappe.get_all(
		"Fixed Asset",
		filters={"monitoring_enabled": 1},
		fields=["name"],
		limit_page_length=5000,
	)
	for row in assets:
		try:
			recompute_asset_reliability_and_health(row.name)
			if is_predictive_rules_enabled():
				run_predictive_rules_for_asset(row.name)
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"EAM reliability job failed for {row.name}")
	run_scheduler_capacity_checks()


def run_scheduler_capacity_checks():
	"""Create planning alerts for overdue/overloaded work-order schedules."""
	rows = frappe.get_all(
		"Asset Work Order",
		filters={"docstatus": ["<", 2], "status": ["in", ["Planned", "Assigned", "In Progress"]]},
		fields=["name", "asset", "company", "branch", "assigned_to", "sla_due", "priority"],
		limit_page_length=10000,
	)
	load = {}
	for r in rows:
		user = r.assigned_to or "Unassigned"
		load[user] = load.get(user, 0) + 1
		if r.sla_due and get_datetime(r.sla_due) < get_datetime():
			msg = f"Work order {r.name} is overdue versus SLA due {r.sla_due}."
			_create_scheduler_alert_if_missing(r, "High", msg, "SLA Breach")

	for user, count in load.items():
		if count < 12:
			continue
		target = next((x for x in rows if (x.assigned_to or "Unassigned") == user), None)
		if not target:
			continue
		msg = f"Technician {user} has {count} active work orders (capacity warning)."
		_create_scheduler_alert_if_missing(target, "Medium", msg, "Capacity Warning")


def _create_scheduler_alert_if_missing(work_order_row, severity: str, message: str, alert_type: str):
	exists = frappe.db.exists(
		"Asset Alert",
		{
			"asset": work_order_row.asset,
			"status": "Open",
			"alert_type": alert_type,
			"message": message,
		},
	)
	if exists:
		return
	frappe.get_doc(
		{
			"doctype": "Asset Alert",
			"asset": work_order_row.asset,
			"company": work_order_row.company,
			"branch": work_order_row.branch,
			"alert_time": get_datetime(),
			"alert_type": alert_type,
			"severity": severity,
			"status": "Open",
			"message": message,
			"source": "scheduler_capacity",
			"reference_doctype": "Asset Work Order",
			"reference_name": work_order_row.name,
		}
	).insert(ignore_permissions=True)


def run_hourly_condition_monitoring_jobs():
	"""Evaluate latest meter readings against threshold profiles and raise alerts."""
	if not is_scheduler_enabled() or not is_condition_monitoring_enabled():
		return
	profiles = frappe.get_all(
		"Asset Threshold Profile",
		filters={"enabled": 1},
		fields=["name", "company", "branch", "meter_type", "warning_threshold", "critical_threshold", "comparison_operator"],
		limit_page_length=5000,
	)
	for p in profiles:
		latest = frappe.get_all(
			"Asset Meter Reading",
			filters={"company": p.company, "meter_type": p.meter_type},
			fields=["name", "asset", "company", "branch", "value", "reading_time"],
			order_by="reading_time desc",
			limit_page_length=1,
		)
		if not latest:
			continue
		r = latest[0]
		value = float(r.value or 0.0)
		op = (p.comparison_operator or ">").strip()
		def _hit(threshold):
			if threshold is None:
				return False
			t = float(threshold or 0.0)
			if op == ">":
				return value > t
			if op == "<":
				return value < t
			if op == ">=":
				return value >= t
			if op == "<=":
				return value <= t
			return value > t

		severity = None
		if _hit(p.critical_threshold):
			severity = "Critical"
		elif _hit(p.warning_threshold):
			severity = "High"
		if not severity:
			continue

		msg = f"{p.meter_type} value {value} breached {severity.lower()} threshold."
		exists = frappe.db.exists(
			"Asset Alert",
			{"asset": r.asset, "status": "Open", "alert_type": "Threshold Breach", "message": msg},
		)
		if exists:
			continue
		frappe.get_doc(
			{
				"doctype": "Asset Alert",
				"asset": r.asset,
				"company": r.company,
				"branch": r.branch,
				"alert_time": get_datetime(),
				"alert_type": "Threshold Breach",
				"severity": severity,
				"status": "Open",
				"message": msg,
				"source": "hourly_monitor",
				"reference_doctype": "Asset Meter Reading",
				"reference_name": r.name,
			}
		).insert(ignore_permissions=True)


def run_daily_hotel_asset_jobs():
	"""Hotel-vertical housekeeping: warranty expiry alerts, etc."""
	if not is_scheduler_enabled():
		return
	if not site_has_any_hotel_assets_company():
		return
	try:
		from omnexa_fixed_assets.hotel_notifications import create_warranty_expiry_alerts

		create_warranty_expiry_alerts(lookahead_days=30)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Hotel daily asset jobs failed")
