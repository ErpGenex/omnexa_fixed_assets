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
		"capitalization_journal_entry": ["is", "set"]}
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
				"posting_date": pd
	},
		)
		if exists:
			skipped.append({"asset": a.name, "reason": "already_posted_on_date"
	})
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
			skipped.append({"asset": a.name, "reason": "zero_or_no_remaining_depreciation"
	})
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Fixed Asset Depreciation Entry",
				"naming_series": "FADP-.#####",
				"company": a.company,
				"branch": a.branch,
				"posting_date": pd,
				"fixed_asset": a.name,
				"depreciation_amount": amount
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
		"skipped": skipped
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
			"payload_json": payload_json
	}
	)
	doc.insert(ignore_permissions=True)
	if meter_type == "Runtime":
		asset_doc.db_set("runtime_hours", flt(asset_doc.runtime_hours) + flt(value), update_modified=False)
	return {"ok": True, "reading": doc.name, "asset": asset
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_asset_health_payload(asset: str):
	if not asset:
		frappe.throw(_("Asset is required."))
	if not frappe.db.exists("Fixed Asset", asset):
		return {"ok": False, "message": "Asset not found"
	}
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
	return {"ok": True, "asset": row
	}


@frappe.whitelist(methods=["POST"])
def run_asset_reliability_recompute(asset: str | None = None, limit: int | str = 100):
	"""On-demand reliability/health recompute endpoint."""
	if not is_reliability_enabled() and not is_health_engine_enabled():
		return {"ok": False, "message": "Reliability and health engines are disabled by feature flags."
	}
	out = []
	if asset:
		out.append(recompute_asset_reliability_and_health(asset))
	else:
		rows = frappe.get_all("Fixed Asset", filters={"monitoring_enabled": 1
	}, fields=["name"], limit_page_length=max(1, cint(limit)))
		for r in rows:
			out.append(recompute_asset_reliability_and_health(r.name))
	return {"ok": True, "processed": len(out), "results": out
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_eam_feature_flags():
	return {
		"ok": True,
		"enable_condition_monitoring": is_condition_monitoring_enabled(),
		"enable_reliability": is_reliability_enabled(),
		"enable_health_engine": is_health_engine_enabled(),
		"enable_hotel_asset_management": is_hotel_asset_management_enabled()
	}


@frappe.whitelist(methods=["POST"])
def seed_hotel_demo_assets_from_company(
	company: str,
	branch: str | None = None,
	count: int | str | None = 50,
	property_name: str | None = None,
	guest_floors: int | str | None = 6,
	guest_rooms_per_floor: int | str | None = 20,
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
		guest_floors=cint(guest_floors or 6),
		guest_rooms_per_floor=cint(guest_rooms_per_floor or 20),
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
		"functional_areas_created": out.get("functional_areas_created"),
		"guest_rooms_created": out.get("guest_rooms_created"),
		"service_locations_created": out.get("service_locations_created"),
		"total_locations": out.get("total_locations"),
	}


def _resolve_hotel_dashboard_scope(
	company: str | None, branch: str | None
) -> tuple[str | None, str | None]:
	"""Use desk navbar company/branch when the dashboard does not pass explicit values."""
	from omnexa_core.omnexa_core.session_context import get_view_context

	ctx = get_view_context()
	if not company:
		company = ctx.get("company")
	if branch is None or branch == "":
		if ctx.get("view_all_branches"):
			branch = None
		else:
			branch = ctx.get("branch")
	return company, branch


def _hotel_dashboard_context_label(company: str | None, branch: str | None) -> str:
	from omnexa_core.omnexa_core.session_context import get_view_context

	ctx = get_view_context()
	if ctx.get("label"):
		return ctx["label"]
	if company and branch:
		branch_label = frappe.db.get_value("Branch", branch, "branch_name") or branch
		return f"{company} · {branch_label}"
	return company or ""


@frappe.whitelist()
def get_hotel_assets_portal_context(company: str | None = None, branch: str | None = None):
	"""Full director-style portal payload for the hotel assets desk page."""
	if frappe.session.user in ("", "Guest"):
		frappe.throw(_("Login required"))

	company, branch = _resolve_hotel_dashboard_scope(company, branch)
	if not company or not frappe.db.exists("Company", company):
		return {
			"ok": False,
			"message": _("Select a company in the desk navbar to view this dashboard."),
		}
	if not is_hotel_vertical_active_for_company(company):
		return {
			"ok": False,
			"message": _(
				"Set this company's Business Activity / Industry to Hotel Assets, or enable the site hotel flag."
			),
		}

	from omnexa_fixed_assets.hotel_portal_dashboard import build_hotel_portal_context

	portal = build_hotel_portal_context(company, branch)
	return {
		"ok": True,
		"company": company,
		"branch": branch,
		"context_label": _hotel_dashboard_context_label(company, branch),
		**portal,
	}


@frappe.whitelist()
def get_hotel_assets_dashboard_data(company: str | None = None, branch: str | None = None):
	"""Aggregate KPIs and breakdowns for the hotel asset management dashboard."""
	if frappe.session.user in ("", "Guest"):
		frappe.throw(_("Login required"))

	company, branch = _resolve_hotel_dashboard_scope(company, branch)
	if not company or not frappe.db.exists("Company", company):
		return {
			"ok": False,
			"message": _("Select a company in the desk navbar to view this dashboard."),
		}
	if not is_hotel_vertical_active_for_company(company):
		return {
			"ok": False,
			"message": _(
				"Set this company's Business Activity / Industry to Hotel Assets, or enable the site hotel flag."
			),
		}

	params = {"company": company}
	branch_filter = ""
	if branch:
		if not frappe.db.exists("Branch", branch):
			frappe.throw(_("Branch {0} does not exist.").format(branch))
		if frappe.db.get_value("Branch", branch, "company") != company:
			frappe.throw(_("Branch does not belong to this company."))
		params["branch"] = branch
		branch_filter = "AND fa.branch = %(branch)s"

	hotel_asset_filter = "fa.company = %(company)s AND IFNULL(fa.hotel_property, '') != ''" + f" {branch_filter}"

	total_assets = frappe.db.sql(
		f"SELECT COUNT(*) FROM `tabFixed Asset` fa WHERE {hotel_asset_filter}",
		params,
	)[0][0]

	total_nbv = frappe.db.sql(
		f"SELECT IFNULL(SUM(fa.net_book_value), 0) FROM `tabFixed Asset` fa WHERE {hotel_asset_filter}",
		params,
	)[0][0]

	rfid_tagged = frappe.db.sql(
		f"""
		SELECT COUNT(*) FROM `tabFixed Asset` fa
		WHERE {hotel_asset_filter} AND IFNULL(fa.rfid_tag, '') != ''
		""",
		params,
	)[0][0]

	prop_filters = {"company": company}
	if branch:
		prop_filters["branch"] = branch
	hotel_properties = frappe.db.count("Hotel Property", prop_filters)
	hotel_rooms = frappe.db.count("Hotel Room", {"company": company})

	open_inspections = frappe.db.count(
		"Hotel Asset Inspection",
		{"company": company, "docstatus": 0},
	)

	by_status = frappe.db.sql(
		f"""
		SELECT IFNULL(fa.status, '') AS status, COUNT(*) AS count
		FROM `tabFixed Asset` fa
		WHERE {hotel_asset_filter}
		GROUP BY fa.status
		ORDER BY count DESC
		""",
		params,
		as_dict=True,
	)

	by_property = frappe.db.sql(
		f"""
		SELECT fa.hotel_property, COUNT(*) AS count
		FROM `tabFixed Asset` fa
		WHERE {hotel_asset_filter}
		GROUP BY fa.hotel_property
		ORDER BY count DESC
		LIMIT 12
		""",
		params,
		as_dict=True,
	)

	by_floor = frappe.db.sql(
		f"""
		SELECT IFNULL(hr.floor, '') AS floor, COUNT(*) AS count
		FROM `tabFixed Asset` fa
		LEFT JOIN `tabHotel Room` hr ON hr.name = fa.hotel_room
		WHERE {hotel_asset_filter}
		GROUP BY hr.floor
		ORDER BY count DESC
		LIMIT 12
		""",
		params,
		as_dict=True,
	)

	reports = [
		{"label": "Hotel Assets by Floor", "link": "Hotel Assets by Floor", "type": "Report"},
		{"label": "Assets by Room", "link": "Assets by Room", "type": "Report"},
		{"label": "Hotel Operational Asset Status", "link": "Hotel Operational Asset Status", "type": "Report"},
		{"label": "Hotel Inspection Summary", "link": "Hotel Inspection Summary", "type": "Report"},
		{"label": "Missing Assets", "link": "Missing Assets", "type": "Report"},
		{"label": "Unscanned Assets", "link": "Unscanned Assets", "type": "Report"},
		{"label": "Hotel Asset Depreciation", "link": "Hotel Asset Depreciation", "type": "Report"},
		{"label": "Fixed Asset", "link": "List/Fixed Asset", "type": "DocType"},
		{"label": "Hotel Property", "link": "List/Hotel Property", "type": "DocType"},
	]

	return {
		"ok": True,
		"company": company,
		"branch": branch,
		"context_label": _hotel_dashboard_context_label(company, branch),
		"kpis": {
			"total_assets": total_assets,
			"total_nbv": flt(total_nbv),
			"rfid_tagged": rfid_tagged,
			"hotel_properties": hotel_properties,
			"hotel_rooms": hotel_rooms,
			"open_inspections": open_inspections,
		},
		"by_status": by_status,
		"by_property": by_property,
		"by_floor": by_floor,
		"reports": reports,
	}


def _require_hotel_feature_enabled():
	enforce_hotel_feature_enabled()


@frappe.whitelist(methods=["POST"])
def scan_asset(
	asset: str | None = None,
	provider: str | None = None,
	reader_device: str | None = None,
	location_text: str | None = None,
	signal_strength: float | str | None = None,
	scan_result: str | None = "Seen",
	rfid_tag: str | None = None,
	epc: str | None = None,
	uid: str | None = None,
):
	"""Hotel endpoint: register RFID scan and update asset scan status."""
	_require_hotel_feature_enabled()
	from omnexa_fixed_assets.utils.rfid.event_processor import (
		process_rfid_scan,
		resolve_entity_from_identifiers,
	)

	tag = rfid_tag or epc or uid
	entity = resolve_entity_from_identifiers(asset, tag)
	if not entity and not tag and not asset:
		frappe.throw(_("Asset, linen RFID tag, or identifier is required."))

	resolved_asset = entity[1] if entity and entity[0] == "asset" else (asset or "")
	normalized = get_rfid_adapter(provider).normalize_scan(
		{
			"asset": resolved_asset,
			"rfid_tag": tag,
			"reader_device": reader_device,
			"location_text": location_text,
			"signal_strength": signal_strength,
			"scan_result": scan_result,
		}
	)
	result = process_rfid_scan(normalized, provider=provider)
	if not result.ok:
		frappe.throw(result.message or _("Unable to process RFID scan."))

	return {
		"ok": True,
		"entity_type": result.entity_type,
		"scan_log": result.scan_log,
		"asset": result.asset,
		"linen_item": result.linen_item,
		"scan_status": result.scan_status,
		"duplicate": result.duplicate,
		"movement_log": result.movement_log,
		"confidence_score": result.confidence_score,
	}


@frappe.whitelist(methods=["POST"])
def sync_offline_rfid_events(
	events=None,
	provider: str | None = None,
	gateway_id: str | None = None,
	api_token: str | None = None,
):
	"""Offline PWA / gateway buffer sync with external event ids."""
	return ingest_rfid_events_bulk(
		events=events, provider=provider, gateway_id=gateway_id, api_token=api_token
	)


@frappe.whitelist(methods=["GET", "POST"])
def get_live_asset_map(company: str | None = None, branch: str | None = None):
	"""Live map payload: rooms, assets, readers, recent movements."""
	_require_hotel_feature_enabled()
	from omnexa_fixed_assets.utils.rfid.event_processor import get_live_map_payload
	from omnexa_core.omnexa_core.user_context import get_navbar_form_defaults

	defaults = get_navbar_form_defaults()
	company = company or defaults.get("company")
	branch = branch or defaults.get("branch")
	if not company:
		frappe.throw(_("Company is required."))
	return {"ok": True, "company": company, "branch": branch, **get_live_map_payload(company, branch)}


@frappe.whitelist(methods=["GET", "POST"])
def get_linen_dashboard(company: str | None = None, branch: str | None = None):
	"""Linen KPIs for dashboard page."""
	_require_hotel_feature_enabled()
	from omnexa_core.omnexa_core.user_context import get_navbar_form_defaults

	defaults = get_navbar_form_defaults()
	company = company or defaults.get("company")
	branch = branch or defaults.get("branch")
	if not company:
		frappe.throw(_("Company is required."))
	filters: dict = {"company": company}
	if branch:
		filters["branch"] = branch

	total = frappe.db.count("Linen Item", filters)
	by_status = frappe.get_all(
		"Linen Item",
		filters=filters,
		fields=["status", "count(name) as count"],
		group_by="status",
	)
	by_type = frappe.get_all(
		"Linen Item",
		filters=filters,
		fields=["linen_type", "count(name) as count"],
		group_by="linen_type",
		order_by="count desc",
		limit=10,
	)
	missing = frappe.db.count("Linen Item", {**filters, "status": "Missing"})
	shortages = frappe.get_all(
		"Linen Shortage Alert",
		filters={**filters, "status": "Open"},
		fields=["name", "linen_type", "missing_quantity", "message", "alert_time"],
		order_by="alert_time desc",
		limit=20,
	)
	replacement = frappe.get_all(
		"Linen Item",
		filters=filters,
		fields=["name", "linen_name", "linen_type", "wash_count", "expected_life_cycles"],
		limit=5000,
	)
	replacement_warnings = [
		r
		for r in replacement
		if int(r.expected_life_cycles or 0) - int(r.wash_count or 0)
		<= int(frappe.conf.get("omnexa_linen_replacement_threshold") or 15)
	]
	return {
		"ok": True,
		"company": company,
		"branch": branch,
		"kpis": {
			"total_linen": total,
			"missing_linen": missing,
			"open_shortages": len(shortages),
			"replacement_warnings": len(replacement_warnings),
		},
		"by_status": by_status,
		"by_type": by_type,
		"shortages": shortages,
		"replacement_warnings": replacement_warnings[:20],
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_asset_heatmap(company: str | None = None, branch: str | None = None, floor: str | None = None):
	"""Floor/zone heatmap densities for hospitality dashboards."""
	_require_hotel_feature_enabled()
	from omnexa_core.omnexa_core.user_context import get_navbar_form_defaults
	from omnexa_fixed_assets.utils.intelligence.heatmap import get_asset_heatmap as _heatmap

	defaults = get_navbar_form_defaults()
	company = company or defaults.get("company")
	branch = branch or defaults.get("branch")
	if not company:
		frappe.throw(_("Company is required."))
	return {"ok": True, "company": company, "branch": branch, **_heatmap(company, branch, floor)}


@frappe.whitelist(methods=["POST"])
def run_hospitality_intelligence(company: str | None = None, branch: str | None = None):
	"""Manually trigger rule-based intelligence (admin/scheduler)."""
	_require_hotel_feature_enabled()
	from omnexa_core.omnexa_core.user_context import get_navbar_form_defaults
	from omnexa_fixed_assets.utils.intelligence.rules_engine import run_hospitality_intelligence as _run

	defaults = get_navbar_form_defaults()
	company = company or defaults.get("company")
	branch = branch or defaults.get("branch")
	if not company:
		frappe.throw(_("Company is required."))
	return {"ok": True, "company": company, "branch": branch, "results": _run(company, branch)}


@frappe.whitelist(methods=["GET", "POST"])
def get_global_hospitality_portfolio(company: str | None = None):
	"""Enterprise multi-property / multi-branch rollup."""
	_require_hotel_feature_enabled()
	from omnexa_core.omnexa_core.user_context import get_navbar_form_defaults
	from omnexa_fixed_assets.utils.intelligence.global_portfolio import get_global_portfolio

	defaults = get_navbar_form_defaults()
	company = company or defaults.get("company")
	if not company:
		frappe.throw(_("Company is required."))
	return {"ok": True, "company": company, **get_global_portfolio(company)}


@frappe.whitelist(methods=["GET", "POST"])
def get_floor_plan(company: str | None = None, branch: str | None = None, floor: str | None = None):
	"""SVG floor plan for live map rendering."""
	_require_hotel_feature_enabled()
	from omnexa_core.omnexa_core.user_context import get_navbar_form_defaults
	from omnexa_fixed_assets.utils.intelligence.global_portfolio import get_floor_plan_svg

	defaults = get_navbar_form_defaults()
	company = company or defaults.get("company")
	branch = branch or defaults.get("branch")
	if not company or not floor:
		frappe.throw(_("Company and floor are required."))
	plan = get_floor_plan_svg(company, branch, floor)
	return {"ok": bool(plan), "company": company, "branch": branch, "floor": floor, "plan": plan}


@frappe.whitelist(methods=["GET", "POST"])
def get_predictive_analytics(company: str | None = None, branch: str | None = None):
	"""Predictive risk scores and forecasts (statistical, not ML)."""
	_require_hotel_feature_enabled()
	from omnexa_core.omnexa_core.user_context import get_navbar_form_defaults
	from omnexa_fixed_assets.utils.intelligence.predictive import run_predictive_analytics

	defaults = get_navbar_form_defaults()
	company = company or defaults.get("company")
	branch = branch or defaults.get("branch")
	if not company:
		frappe.throw(_("Company is required."))
	return {"ok": True, "company": company, "branch": branch, "analytics": run_predictive_analytics(company, branch)}


@frappe.whitelist(methods=["POST"])
def ingest_rfid_events_bulk(
	events=None,
	provider: str | None = None,
	gateway_id: str | None = None,
	api_token: str | None = None,
):
	"""Batch RFID ingest for gateways/readers (dedup + movement per event)."""
	_require_hotel_feature_enabled()
	import json

	from omnexa_fixed_assets.utils.rfid.device_auth import validate_gateway_request
	from omnexa_fixed_assets.utils.rfid.event_processor import process_rfid_events_bulk

	validate_gateway_request(gateway_id, api_token)
	if isinstance(events, str):
		events = json.loads(events)
	if not isinstance(events, list):
		frappe.throw(_("events must be a JSON list."))
	result = process_rfid_events_bulk(events, provider=provider)
	try:
		from omnexa_fixed_assets.utils.intelligence.rules_engine import log_intelligence_audit
		from omnexa_core.omnexa_core.user_context import get_navbar_form_defaults

		defaults = get_navbar_form_defaults()
		if defaults.get("company"):
			log_intelligence_audit(
				defaults["company"],
				"RFID Event",
				f"Bulk ingest processed={result.get('processed')} created={result.get('created')}",
				branch=defaults.get("branch"),
				source="API",
				device=gateway_id,
			)
	except Exception:
		pass
	return {"ok": True, **result}


@frappe.whitelist(methods=["POST"])
def rotate_rfid_gateway_token(gateway_id: str):
	"""Rotate API token for an RFID Gateway."""
	_require_hotel_feature_enabled()
	if not frappe.has_permission("RFID Gateway", "write"):
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	from omnexa_fixed_assets.utils.rfid.device_auth import rotate_gateway_token

	return rotate_gateway_token(gateway_id)


@frappe.whitelist(methods=["GET", "POST"])
def get_live_rfid_movements(company: str | None = None, branch: str | None = None, limit: int | str = 50):
	"""Recent RFID-driven movements for live dashboard / WebSocket clients."""
	_require_hotel_feature_enabled()
	from omnexa_fixed_assets.utils.rfid.event_processor import get_live_movements
	from omnexa_core.omnexa_core.user_context import get_navbar_form_defaults

	defaults = get_navbar_form_defaults()
	company = company or defaults.get("company")
	branch = branch or defaults.get("branch")
	if not company:
		frappe.throw(_("Company is required."))
	return {
		"ok": True,
		"company": company,
		"branch": branch,
		"movements": get_live_movements(company, branch, limit=int(limit or 50)),
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_asset_lifecycle_timeline(asset: str, limit: int | str = 50):
	"""Lifecycle events for desk timeline and mobile clients."""
	if not asset:
		frappe.throw(_("Asset is required."))
	from omnexa_fixed_assets.utils.asset_lifecycle import get_asset_lifecycle_timeline as _timeline

	return {"ok": True, "asset": asset, "events": _timeline(asset, limit=int(limit or 50))}


@frappe.whitelist(methods=["GET", "POST"])
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
		return {"ok": False, "message": "Asset not found"
	}
	last_scan = frappe.get_all(
		"RFID Scan Log",
		filters={"fixed_asset": asset
	},
		fields=["name", "scan_time", "location_text", "reader_device", "scan_result"],
		order_by="scan_time desc",
		limit_page_length=1,
	)
	return {"ok": True, "asset": asset_row, "last_scan": last_scan[0] if last_scan else None
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_qr_svg_data_uri(payload: str):
	"""Generate QR SVG as a data-uri for Desk form rendering."""
	if not payload:
		return {"data_uri": None
	}
	try:
		from pyqrcode import create as qrcreate
	except Exception:
		return {"data_uri": None
	}

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
	return {"ok": True, "asset": doc.name, "housekeeping_status": housekeeping_status, "engineering_status": engineering_status
	}


def _map_inspection_to_condition_state(condition_status: str | None) -> str:
	"""Map hotel inspection vocabulary to EAM condition_state on Fixed Asset."""
	mapping = {
		"Excellent": "Normal",
		"Good": "Normal",
		"Fair": "Watch",
		"Poor": "Alert",
		"Critical": "Critical",
	}
	return mapping.get((condition_status or "").strip(), "Normal")


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
			"notes": notes
	}
	)
	ins.insert(ignore_permissions=True)
	asset_doc.db_set(
		"condition_state",
		_map_inspection_to_condition_state(condition_status),
		update_modified=False,
	)
	return {"ok": True, "inspection": ins.name, "asset": asset_doc.name, "condition_status": condition_status
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_asset_command_center(company: str, branch: str | None = None):
	"""Command Center payload: critical assets, alerts, health/risk and compliance KPIs."""
	if not company:
		frappe.throw(_("Company is required."))
	asset_filters = {"company": company
	}
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
		filters={**asset_filters, "status": "Open"
	},
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

	portfolio_health = frappe.db.sql(
		"""
		select avg(coalesce(health_score, 0)) as portfolio_health_index,
			count(*) as asset_count
		from `tabFixed Asset`
		where company=%s {branch_sql}
		""".format(branch_sql="and branch=%s" if branch else ""),
		(company, branch) if branch else (company,),
		as_dict=True,
	)[0]

	hospitality_kpis = _hospitality_command_center_kpis(asset_filters)

	return {
		"ok": True,
		"critical_assets": critical_assets,
		"active_alerts": open_alerts,
		"health_distribution": health_distribution,
		"portfolio_health_index": round(float(portfolio_health.portfolio_health_index or 0), 2),
		"portfolio_asset_count": int(portfolio_health.asset_count or 0),
		"inspection_compliance_rate": compliance_rate,
		"hospitality": hospitality_kpis,
	}


def _hospitality_command_center_kpis(asset_filters: dict) -> dict:
	"""Extended KPIs per spec §42 Hospitality Asset Command Center."""
	total_assets = frappe.db.count("Fixed Asset", asset_filters)
	rfid_tagged = frappe.db.count("Fixed Asset", {**asset_filters, "rfid_tag": ["is", "set"]})
	missing_assets = frappe.db.count("Fixed Asset", {**asset_filters, "scan_status": ["in", ["Missing", "Mismatch"]]})
	unauthorized = frappe.db.count(
		"Asset Alert",
		{**asset_filters, "alert_type": "Unauthorized Movement", "status": "Open"},
	)
	maintenance = frappe.db.count(
		"Fixed Asset",
		{**asset_filters, "status": "under_maintenance"},
	)
	critical = frappe.db.count(
		"Fixed Asset",
		{**asset_filters, "criticality": ["in", ["High", "Safety Critical"]]},
	)

	rfid_online = rfid_offline = 0
	if frappe.db.exists("DocType", "RFID Reader"):
		rfid_online = frappe.db.count("RFID Reader", {**asset_filters, "status": "Online"})
		rfid_offline = frappe.db.count("RFID Reader", {**asset_filters, "status": "Offline"})

	missing_linen = 0
	total_linen = 0
	if frappe.db.exists("DocType", "Linen Item"):
		total_linen = frappe.db.count("Linen Item", asset_filters)
		missing_linen = frappe.db.count("Linen Item", {**asset_filters, "status": "Missing"})

	since = frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-15)
	moving_now = frappe.db.count(
		"Fixed Asset Movement Log",
		{**asset_filters, "creation": [">=", since], "reference_doctype": "RFID Scan Log"},
	)

	open_recommendations = frappe.db.count(
		"Asset Recommendation",
		{**asset_filters, "status": "Open", "source": "hospitality_intelligence"},
	)

	return {
		"total_assets": total_assets,
		"tracked_assets": rfid_tagged,
		"untracked_assets": max(total_assets - rfid_tagged, 0),
		"rfid_online": rfid_online,
		"rfid_offline": rfid_offline,
		"assets_moving_now": moving_now,
		"unauthorized_movements": unauthorized,
		"missing_assets": missing_assets,
		"missing_linen": missing_linen,
		"total_linen": total_linen,
		"critical_assets_count": critical,
		"maintenance_assets": maintenance,
		"open_intelligence_recommendations": open_recommendations,
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_reliability_analytics_workbench(company: str, branch: str | None = None, from_date: str | None = None, to_date: str | None = None):
	"""Reliability workbench payload: mtbf/mttr trends + failure pareto."""
	if not company:
		frappe.throw(_("Company is required."))
	filters = {"company": company
	}
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
	return {"ok": True, "trends": trends, "failure_pareto": failure_pareto
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_scheduler_board_payload(company: str, branch: str | None = None):
	"""Maximo-style scheduling board payload for calendar/gantt/technician assignments."""
	if not company:
		frappe.throw(_("Company is required."))
	filters = {"company": company
	}
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
	return {"ok": True, "work_orders": work_orders, "capacity": capacity
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_condition_monitoring_console(company: str, branch: str | None = None, asset: str | None = None, limit: int | str = 200):
	"""Condition monitoring payload: latest readings, alerts, and trend samples."""
	if not company:
		frappe.throw(_("Company is required."))
	filters = {"company": company
	}
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
		filters={**filters, "status": "Open"
	},
		fields=["name", "asset", "alert_type", "severity", "alert_time", "message"],
		order_by="alert_time desc",
		limit_page_length=100,
	)
	return {"ok": True, "readings": readings, "alerts": alerts
	}


@frappe.whitelist(methods=["POST"])
def create_work_order_from_alert(alert_name: str, work_order_type: str = "Inspection-Triggered", priority: str = "High"):
	"""Create maintenance work order from an open alert."""
	if not alert_name:
		frappe.throw(_("Alert name is required."))
	alert = frappe.get_doc("Asset Alert", alert_name)
	if alert.status == "Closed":
		return {"ok": False, "message": "Alert is already closed."}

	from omnexa_fixed_assets.utils.predictive_wo import create_predictive_work_order

	wo_type = work_order_type or "Inspection-Triggered"
	if wo_type == "Predictive":
		result = create_predictive_work_order(
			alert.asset,
			f"Auto-created from alert {alert.name}: {alert.message or ''}",
			priority=priority,
			source=f"alert:{alert.name}",
		)
		if result.get("ok"):
			alert.db_set("status", "Acknowledged", update_modified=False)
		return result

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
			"description": f"Auto-created from alert {alert.name}: {alert.message or ''}"
	}
	)
	wo.insert(ignore_permissions=True)
	alert.db_set("status", "Acknowledged", update_modified=False)
	return {"ok": True, "work_order": wo.name, "alert": alert.name
	}


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


# ---------------------------------------------------------------------------
# Asset Lifecycle Wizards
# ---------------------------------------------------------------------------


@frappe.whitelist(methods=["GET", "POST"])
def get_wizard_catalog() -> dict:
	"""Return all wizard definitions for desk UI."""
	from omnexa_fixed_assets.utils.wizard.catalog import get_catalog

	return {"ok": True, "wizards": get_catalog()}


@frappe.whitelist(methods=["POST"])
def start_wizard(wizard_type: str, company: str | None = None, branch: str | None = None) -> dict:
	"""Create a draft wizard session."""
	from omnexa_core.omnexa_core.user_context import get_navbar_form_defaults
	from omnexa_fixed_assets.utils.wizard.engine import start_wizard as _start

	defaults = get_navbar_form_defaults()
	company = company or defaults.get("company")
	branch = branch if branch is not None else defaults.get("branch")
	if not company:
		frappe.throw(_("Company is required."))
	session = _start(wizard_type, company, branch)
	return {"ok": True, "session": session}


@frappe.whitelist(methods=["GET", "POST"])
def get_wizard_session(session_name: str) -> dict:
	from omnexa_fixed_assets.utils.wizard.engine import get_session

	return {"ok": True, "session": get_session(session_name)}


@frappe.whitelist(methods=["POST"])
def save_wizard_step(session_name: str, step_key: str, payload: str | dict | None = None) -> dict:
	"""Validate and persist one wizard step."""
	import json

	from omnexa_fixed_assets.utils.wizard.engine import save_wizard_step as _save

	if isinstance(payload, str):
		try:
			payload = json.loads(payload) if payload else {}
		except Exception:
			frappe.throw(_("Invalid step payload JSON."))
	return _save(session_name, step_key, payload or {})


@frappe.whitelist(methods=["POST"])
def submit_wizard(session_name: str) -> dict:
	"""Finalize wizard — atomic execution against existing DocTypes."""
	from omnexa_fixed_assets.utils.wizard.engine import submit_wizard as _submit

	return _submit(session_name)


@frappe.whitelist(methods=["POST"])
def cancel_wizard(session_name: str) -> dict:
	from omnexa_fixed_assets.utils.wizard.engine import cancel_wizard as _cancel

	return _cancel(session_name)


@frappe.whitelist(methods=["GET", "POST"])
def list_wizard_drafts(
	company: str | None = None, wizard_type: str | None = None, limit: int | str = 20
) -> dict:
	from omnexa_fixed_assets.utils.wizard.engine import list_wizard_drafts as _list

	return {"ok": True, "drafts": _list(company=company, wizard_type=wizard_type, limit=cint(limit))}


@frappe.whitelist(methods=["GET", "POST"])
def resolve_asset_for_wizard(identifier: str) -> dict:
	"""Resolve asset by ID, RFID, barcode, or tag."""
	from omnexa_fixed_assets.utils.wizard.executors import resolve_asset

	row = resolve_asset(identifier)
	return {"ok": bool(row), "asset": row}


@frappe.whitelist(methods=["GET", "POST"])
def preview_wizard_depreciation(asset: str, posting_date: str | None = None) -> dict:
	"""Preview monthly depreciation amount for depreciation wizard."""
	if not asset:
		frappe.throw(_("Asset is required."))
	pd = getdate(posting_date or today())
	amount = suggest_monthly_depreciation(asset, posting_date=pd)
	return {"ok": True, "posting_date": str(pd), "depreciation_amount": amount}
