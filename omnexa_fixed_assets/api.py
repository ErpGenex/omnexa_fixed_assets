# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, today

from base64 import b64encode
from io import BytesIO

from omnexa_fixed_assets.utils.feature_flags import (
	is_condition_monitoring_enabled,
	is_hotel_asset_management_enabled,
	is_health_engine_enabled,
	is_hotel_vertical_active_for_company,
	is_reliability_enabled,
)
from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled
from omnexa_fixed_assets.utils.reliability_health_engine import recompute_asset_reliability_and_health
from omnexa_fixed_assets.utils.ias16 import suggest_monthly_depreciation
from omnexa_fixed_assets.utils.rfid.factory import get_rfid_adapter


@frappe.whitelist()
def run_monthly_depreciation_batch(
	company: str,
	posting_date: str | None = None,
	branch: str | None = None,
	submit_entries: int | str = 1,
	limit: int | str = 500,
):
	"""Create monthly depreciation entries for eligible cost-model assets.

	Idempotency: skip asset if a submitted depreciation entry already exists on `posting_date`.
	Returns a small summary payload for UI/script usage.
	"""
	pd = getdate(posting_date or today())
	submit_flag = cint(submit_entries) == 1
	max_rows = max(1, min(cint(limit), 2000))

	filters = {
		"company": company,
		"measurement_model": "Cost Model",
		"depreciation_method": ["not in", ["", "None"]],
		"status": ["in", ["acquired", "tagged", "in_use", "transferred", "under_maintenance"]],
		"capitalization_journal_entry": ["is", "set"],
	}
	if branch:
		filters["branch"] = branch

	assets = frappe.get_all(
		"Fixed Asset",
		filters=filters,
		fields=[
			"name",
			"company",
			"branch",
			"depreciation_method",
			"acquisition_cost",
			"salvage_value",
			"accumulated_depreciation",
			"useful_life_months",
			"declining_balance_rate_annual",
			"total_estimated_units",
		],
		limit=max_rows,
		order_by="modified asc",
	)

	created: list[str] = []
	submitted: list[str] = []
	skipped: list[dict] = []

	for a in assets:
		exists = frappe.db.exists(
			"Fixed Asset Depreciation Entry",
			{
				"docstatus": 1,
				"fixed_asset": a.name,
				"posting_date": pd,
			},
		)
		if exists:
			skipped.append({"asset": a.name, "reason": "already_posted_on_date"})
			continue

		amount = suggest_monthly_depreciation(
			method=a.depreciation_method or "",
			cost=flt(a.acquisition_cost),
			salvage=flt(a.salvage_value),
			accumulated_depreciation=flt(a.accumulated_depreciation),
			useful_life_months=a.useful_life_months,
			annual_declining_rate_percent=flt(a.declining_balance_rate_annual),
			total_estimated_units=a.total_estimated_units,
			units_this_period=None,
		)
		if amount <= 0:
			skipped.append({"asset": a.name, "reason": "zero_or_no_remaining_depreciation"})
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Fixed Asset Depreciation Entry",
				"naming_series": "FADP-.#####",
				"company": a.company,
				"branch": a.branch,
				"posting_date": pd,
				"fixed_asset": a.name,
				"depreciation_amount": amount,
			}
		)
		doc.insert()
		created.append(doc.name)
		if submit_flag:
			doc.submit()
			submitted.append(doc.name)

	return {
		"posting_date": str(pd),
		"created_count": len(created),
		"submitted_count": len(submitted),
		"skipped_count": len(skipped),
		"created": created,
		"submitted": submitted,
		"skipped": skipped,
	}


@frappe.whitelist()
def run_auto_depreciation_policy_now(policy_name: str, posting_date: str | None = None):
	"""Run one auto-depreciation policy immediately from its form."""
	if not policy_name:
		frappe.throw(_("Policy name is required."))

	policy = frappe.get_doc("Fixed Asset Auto Depreciation Policy", policy_name)
	if not policy.enabled:
		frappe.throw(_("This policy is disabled."), title=_("Auto Depreciation"))

	result = run_monthly_depreciation_batch(
		company=policy.company,
		branch=policy.branch,
		posting_date=posting_date,
		submit_entries=1 if policy.submit_entries else 0,
		limit=policy.max_assets_per_run or 500,
	)
	status = "Success" if result.get("created_count") else "No Data"
	message = (
		f"created={result.get('created_count', 0)}, "
		f"submitted={result.get('submitted_count', 0)}, "
		f"skipped={result.get('skipped_count', 0)}"
	)
	policy.db_set("last_target_posting_date", result.get("posting_date"), update_modified=False)
	policy.db_set("last_run_at", get_datetime(), update_modified=False)
	policy.db_set("last_run_status", status, update_modified=False)
	policy.db_set("last_run_message", message, update_modified=False)
	return result


@frappe.whitelist(methods=["POST"])
def ingest_asset_meter_reading(
	asset: str,
	meter_type: str,
	value: float | str,
	reading_time: str | None = None,
	unit: str | None = None,
	source: str | None = None,
	quality_score: float | str | None = None,
	payload_json: str | None = None,
):
	"""Telemetry ingestion endpoint (industrial connector friendly)."""
	if not asset:
		frappe.throw(_("Asset is required."))
	if not frappe.db.exists("Fixed Asset", asset):
		frappe.throw(_("Asset does not exist."))
	asset_doc = frappe.get_doc("Fixed Asset", asset)
	doc = frappe.get_doc(
		{
			"doctype": "Asset Meter Reading",
			"asset": asset,
			"company": asset_doc.company,
			"branch": asset_doc.branch,
			"reading_time": get_datetime(reading_time or get_datetime()),
			"meter_type": meter_type,
			"value": flt(value),
			"unit": unit,
			"source": source or "api",
			"quality_score": flt(quality_score) if quality_score is not None else None,
			"payload_json": payload_json,
		}
	)
	doc.insert(ignore_permissions=True)
	if meter_type == "Runtime":
		asset_doc.db_set("runtime_hours", flt(asset_doc.runtime_hours) + flt(value), update_modified=False)
	return {"ok": True, "reading": doc.name, "asset": asset}


@frappe.whitelist(methods=["GET", "POST"])
def get_asset_health_payload(asset: str):
	if not asset:
		frappe.throw(_("Asset is required."))
	if not frappe.db.exists("Fixed Asset", asset):
		return {"ok": False, "message": "Asset not found"}
	fields = [
		"name",
		"asset_name",
		"company",
		"branch",
		"health_score",
		"health_status",
		"reliability_score",
		"mtbf",
		"mttr",
		"availability",
		"risk_score",
		"condition_state",
		"degradation_index",
		"criticality",
		"inspection_due",
	]
	row = frappe.db.get_value("Fixed Asset", asset, fields, as_dict=True)
	return {"ok": True, "asset": row}


@frappe.whitelist(methods=["POST"])
def run_asset_reliability_recompute(asset: str | None = None, limit: int | str = 100):
	"""On-demand reliability/health recompute endpoint."""
	if not is_reliability_enabled() and not is_health_engine_enabled():
		return {"ok": False, "message": "Reliability and health engines are disabled by feature flags."}
	out = []
	if asset:
		out.append(recompute_asset_reliability_and_health(asset))
	else:
		rows = frappe.get_all("Fixed Asset", filters={"monitoring_enabled": 1}, fields=["name"], limit_page_length=max(1, cint(limit)))
		for r in rows:
			out.append(recompute_asset_reliability_and_health(r.name))
	return {"ok": True, "processed": len(out), "results": out}


@frappe.whitelist(methods=["GET"])
def get_eam_feature_flags():
	return {
		"ok": True,
		"enable_condition_monitoring": is_condition_monitoring_enabled(),
		"enable_reliability": is_reliability_enabled(),
		"enable_health_engine": is_health_engine_enabled(),
		"enable_hotel_asset_management": is_hotel_asset_management_enabled(),
	}


@frappe.whitelist(methods=["POST"])
def seed_hotel_demo_assets_from_company(
	company: str,
	branch: str | None = None,
	count: int | str | None = 50,
	property_name: str | None = None,
	with_transfer: int | str = 1,
	with_rfid: int | str = 1,
):
	"""System Manager only: seed demo hotel property, rooms, assets for a branch."""
	if frappe.session.user in ("", "Guest"):
		frappe.throw(_("Login required"))
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only System Manager can run this action."))
	if not company or not frappe.db.exists("Company", company):
		frappe.throw(_("Invalid company."))
	if not branch or not frappe.db.exists("Branch", branch):
		frappe.throw(_("Branch is required — hotel demo is branch-scoped only."))
	if frappe.db.get_value("Branch", branch, "company") != company:
		frappe.throw(_("Branch does not belong to this company."))
	if not is_hotel_vertical_active_for_company(company):
		frappe.throw(
			_("Set this company's Business Activity / Industry to Hotel Assets, or enable the site hotel flag."),
			title=_("Hotel vertical"),
		)

	from omnexa_fixed_assets.scripts.seed_hotel_asset_movements import run as seed_run

	prop = (property_name or "").strip()
	out = seed_run(
		company=company,
		branch=branch,
		count=cint(count or 50),
		property_name=prop or f"فندق تجريبي — {branch}",
		with_transfer=cint(with_transfer) == 1,
		with_rfid=cint(with_rfid) == 1,
		commit=True,
	)
	n = len(out.get("assets") or [])
	return {
		"ok": True,
		"created_count": n,
		"company": out.get("company"),
		"branch": branch,
		"hotel_property": out.get("hotel_property"),
	}


def _require_hotel_feature_enabled():
	enforce_hotel_feature_enabled()


@frappe.whitelist(methods=["POST"])
def scan_asset(
	asset: str,
	provider: str | None = None,
	reader_device: str | None = None,
	location_text: str | None = None,
	signal_strength: float | str | None = None,
	scan_result: str | None = "Seen",
):
	"""Hotel endpoint: register RFID scan and update asset scan status."""
	_require_hotel_feature_enabled()
	if not asset:
		frappe.throw(_("Asset is required."))
	normalized = get_rfid_adapter(provider).normalize_scan(
		{
			"asset": asset,
			"reader_device": reader_device,
			"location_text": location_text,
			"signal_strength": signal_strength,
			"scan_result": scan_result,
		}
	)
	if not normalized.asset:
		frappe.throw(_("Asset is required."))
	asset_doc = frappe.get_doc("Fixed Asset", normalized.asset)
	log = frappe.get_doc(
		{
			"doctype": "RFID Scan Log",
			"company": asset_doc.company,
			"branch": asset_doc.branch,
			"fixed_asset": asset_doc.name,
			"rfid_tag": normalized.rfid_tag or asset_doc.get("rfid_tag"),
			"reader_device": normalized.reader_device,
			"location_text": normalized.location_text,
			"signal_strength": normalized.signal_strength if normalized.signal_strength is not None else None,
			"scan_result": normalized.scan_result or "Seen",
		}
	)
	log.insert(ignore_permissions=True)
	asset_doc.db_set("scan_status", log.scan_result, update_modified=False)
	return {"ok": True, "scan_log": log.name, "asset": asset_doc.name, "scan_status": log.scan_result}


@frappe.whitelist(methods=["GET"])
def locate_asset(asset: str):
	"""Hotel endpoint: return asset location hints from latest RFID scan + room mapping."""
	_require_hotel_feature_enabled()
	if not asset:
		frappe.throw(_("Asset is required."))
	asset_row = frappe.db.get_value(
		"Fixed Asset",
		asset,
		["name", "asset_name", "hotel_property", "hotel_room", "hotel_zone", "scan_status"],
		as_dict=True,
	)
	if not asset_row:
		return {"ok": False, "message": "Asset not found"}
	last_scan = frappe.get_all(
		"RFID Scan Log",
		filters={"fixed_asset": asset},
		fields=["name", "scan_time", "location_text", "reader_device", "scan_result"],
		order_by="scan_time desc",
		limit_page_length=1,
	)
	return {"ok": True, "asset": asset_row, "last_scan": last_scan[0] if last_scan else None}


@frappe.whitelist(methods=["GET", "POST"])
def get_qr_svg_data_uri(payload: str):
	"""Generate QR SVG as a data-uri for Desk form rendering."""
	if not payload:
		return {"data_uri": None}
	try:
		from pyqrcode import create as qrcreate
	except Exception:
		return {"data_uri": None}

	url = qrcreate(payload)
	stream = BytesIO()
	try:
		url.svg(stream, scale=4, background="#fff", module_color="#111")
		svg = stream.getvalue().decode().replace("\n", "")
	finally:
		stream.close()
	b64 = b64encode(svg.encode()).decode()
	return {"data_uri": f"data:image/svg+xml;base64,{b64}"}


@frappe.whitelist(methods=["POST"])
def update_condition(asset: str, housekeeping_status: str | None = None, engineering_status: str | None = None, notes: str | None = None):
	"""Hotel endpoint: update housekeeping/engineering condition flags on asset."""
	_require_hotel_feature_enabled()
	if not asset:
		frappe.throw(_("Asset is required."))
	doc = frappe.get_doc("Fixed Asset", asset)
	if housekeeping_status:
		doc.db_set("housekeeping_status", housekeeping_status, update_modified=False)
	if engineering_status:
		doc.db_set("engineering_status", engineering_status, update_modified=False)
	if notes:
		current = (doc.get("replacement_recommendation") or "").strip()
		doc.db_set("replacement_recommendation", f"{current}\n{notes}".strip(), update_modified=False)
	return {"ok": True, "asset": doc.name, "housekeeping_status": housekeeping_status, "engineering_status": engineering_status}


@frappe.whitelist(methods=["POST"])
def submit_inspection(
	asset: str,
	condition_status: str,
	inspection_date: str | None = None,
	hotel_property: str | None = None,
	hotel_room: str | None = None,
	notes: str | None = None,
):
	"""Hotel endpoint: create inspection row and sync latest condition on asset."""
	_require_hotel_feature_enabled()
	if not asset:
		frappe.throw(_("Asset is required."))
	asset_doc = frappe.get_doc("Fixed Asset", asset)
	ins = frappe.get_doc(
		{
			"doctype": "Hotel Asset Inspection",
			"company": asset_doc.company,
			"branch": asset_doc.branch,
			"fixed_asset": asset_doc.name,
			"hotel_property": hotel_property or asset_doc.get("hotel_property"),
			"hotel_room": hotel_room or asset_doc.get("hotel_room"),
			"inspection_date": inspection_date or today(),
			"inspector": frappe.session.user,
			"condition_status": condition_status,
			"notes": notes,
		}
	)
	ins.insert(ignore_permissions=True)
	asset_doc.db_set("condition_state", condition_status, update_modified=False)
	return {"ok": True, "inspection": ins.name, "asset": asset_doc.name, "condition_status": condition_status}


@frappe.whitelist(methods=["GET", "POST"])
def get_asset_command_center(company: str, branch: str | None = None):
	"""Command Center payload: critical assets, alerts, health/risk and compliance KPIs."""
	if not company:
		frappe.throw(_("Company is required."))
	asset_filters = {"company": company}
	if branch:
		asset_filters["branch"] = branch

	critical_assets = frappe.get_all(
		"Fixed Asset",
		filters={**asset_filters, "criticality": ["in", ["High", "Safety Critical"]]},
		fields=["name", "asset_name", "criticality", "health_status", "health_score", "risk_score", "inspection_due"],
		order_by="risk_score desc, health_score asc",
		limit_page_length=20,
	)
	open_alerts = frappe.get_all(
		"Asset Alert",
		filters={**asset_filters, "status": "Open"},
		fields=["name", "asset", "alert_type", "severity", "alert_time", "message"],
		order_by="alert_time desc",
		limit_page_length=30,
	)
	health_distribution = frappe.db.sql(
		"""
		select coalesce(health_status, 'Unknown') as health_status, count(*) as count
		from `tabFixed Asset`
		where company=%s {branch_sql}
		group by coalesce(health_status, 'Unknown')
		""".format(branch_sql="and branch=%s" if branch else ""),
		(company, branch) if branch else (company,),
		as_dict=True,
	)
	inspection_compliance = frappe.db.sql(
		"""
		select
			count(*) as total,
			sum(case when inspection_due is null or inspection_due >= curdate() then 1 else 0 end) as compliant
		from `tabFixed Asset`
		where company=%s {branch_sql}
		""".format(branch_sql="and branch=%s" if branch else ""),
		(company, branch) if branch else (company,),
		as_dict=True,
	)[0]
	total = int(inspection_compliance.total or 0)
	compliant = int(inspection_compliance.compliant or 0)
	compliance_rate = (compliant / total * 100.0) if total else 100.0
	return {
		"ok": True,
		"critical_assets": critical_assets,
		"active_alerts": open_alerts,
		"health_distribution": health_distribution,
		"inspection_compliance_rate": compliance_rate,
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_reliability_analytics_workbench(company: str, branch: str | None = None, from_date: str | None = None, to_date: str | None = None):
	"""Reliability workbench payload: mtbf/mttr trends + failure pareto."""
	if not company:
		frappe.throw(_("Company is required."))
	filters = {"company": company}
	if branch:
		filters["branch"] = branch
	if from_date:
		filters["as_of_date"] = [">=", getdate(from_date)]
	if to_date:
		if "as_of_date" in filters and isinstance(filters["as_of_date"], list):
			filters["as_of_date"] = ["between", [getdate(from_date), getdate(to_date)]]
		else:
			filters["as_of_date"] = ["<=", getdate(to_date)]

	trends = frappe.get_all(
		"Asset Reliability Trend",
		filters=filters,
		fields=["asset", "as_of_date", "mtbf", "mttr", "availability", "reliability_score"],
		order_by="as_of_date asc",
		limit_page_length=5000,
	)
	failure_pareto = frappe.db.sql(
		"""
		select coalesce(category, 'Uncategorized') as category, count(*) as failures
		from `tabAsset Failure Event`
		where company=%s {branch_sql}
		group by coalesce(category, 'Uncategorized')
		order by failures desc
		""".format(branch_sql="and branch=%s" if branch else ""),
		(company, branch) if branch else (company,),
		as_dict=True,
	)
	return {"ok": True, "trends": trends, "failure_pareto": failure_pareto}


@frappe.whitelist(methods=["GET", "POST"])
def get_scheduler_board_payload(company: str, branch: str | None = None):
	"""Maximo-style scheduling board payload for calendar/gantt/technician assignments."""
	if not company:
		frappe.throw(_("Company is required."))
	filters = {"company": company}
	if branch:
		filters["branch"] = branch
	work_orders = frappe.get_all(
		"Asset Work Order",
		filters=filters,
		fields=[
			"name",
			"asset",
			"work_order_type",
			"priority",
			"status",
			"planned_start",
			"planned_end",
			"assigned_to",
			"sla_due",
		],
		order_by="planned_start asc",
		limit_page_length=5000,
	)
	capacity = {}
	for wo in work_orders:
		user = wo.get("assigned_to") or "Unassigned"
		capacity[user] = capacity.get(user, 0) + 1
	return {"ok": True, "work_orders": work_orders, "capacity": capacity}


@frappe.whitelist(methods=["GET", "POST"])
def get_condition_monitoring_console(company: str, branch: str | None = None, asset: str | None = None, limit: int | str = 200):
	"""Condition monitoring payload: latest readings, alerts, and trend samples."""
	if not company:
		frappe.throw(_("Company is required."))
	filters = {"company": company}
	if branch:
		filters["branch"] = branch
	if asset:
		filters["asset"] = asset
	readings = frappe.get_all(
		"Asset Meter Reading",
		filters=filters,
		fields=["name", "asset", "meter_type", "value", "unit", "reading_time", "source", "quality_score"],
		order_by="reading_time desc",
		limit_page_length=max(1, min(cint(limit), 2000)),
	)
	alerts = frappe.get_all(
		"Asset Alert",
		filters={**filters, "status": "Open"},
		fields=["name", "asset", "alert_type", "severity", "alert_time", "message"],
		order_by="alert_time desc",
		limit_page_length=100,
	)
	return {"ok": True, "readings": readings, "alerts": alerts}


@frappe.whitelist(methods=["POST"])
def create_work_order_from_alert(alert_name: str, work_order_type: str = "Inspection-Triggered", priority: str = "High"):
	"""Create maintenance work order from an open alert."""
	if not alert_name:
		frappe.throw(_("Alert name is required."))
	alert = frappe.get_doc("Asset Alert", alert_name)
	if alert.status == "Closed":
		return {"ok": False, "message": "Alert is already closed."}
	wo = frappe.get_doc(
		{
			"doctype": "Asset Work Order",
			"naming_series": "FAWO-.#####",
			"company": alert.company,
			"branch": alert.branch,
			"asset": alert.asset,
			"work_order_type": work_order_type,
			"priority": priority,
			"status": "Planned",
			"description": f"Auto-created from alert {alert.name}: {alert.message or ''}",
		}
	)
	wo.insert(ignore_permissions=True)
	alert.db_set("status", "Acknowledged", update_modified=False)
	return {"ok": True, "work_order": wo.name, "alert": alert.name}


@frappe.whitelist()
def preview_impairment_adjustment(
	carrying_amount: float, recoverable_amount: float, asset_name: str | None = None
) -> dict:
	"""IAS 36 impairment preview (no GL)."""
	from omnexa_fixed_assets.fi_aa_parity import preview_impairment_adjustment as _preview

	return _preview(carrying_amount, recoverable_amount, asset_name=asset_name)


@frappe.whitelist()
def preview_sector_kpi(scenario: str | None = None, params: str | None = None) -> dict:
	"""SAP Wave C — sector KPI preview (omnexa_core bridge)."""
	from omnexa_core.omnexa_core.vertical_api import preview_sector_kpi as _core_preview

	return _core_preview("fixed_assets", scenario=scenario, params=params)
