# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from omnexa_core.omnexa_core.branch_access import (
	enforce_branch_access,
	permission_query_conditions_for_branch_field,
)
from omnexa_core.omnexa_core.user_context import apply_company_branch_defaults


def enforce_branch_access_for_doc(doc, method=None):
	enforce_branch_access(doc)


def populate_company_branch_from_user_context(doc, method=None):
	apply_company_branch_defaults(doc)


def _query_conditions_for(doctype, user=None, **kwargs):
	import frappe
	meta = frappe.get_meta(doctype)
	if meta.has_field("branch"):
		return permission_query_conditions_for_branch_field(doctype, user)
	return ""


def fixed_asset_category_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Category", user)


def fixed_asset_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset", user)


def fixed_asset_acquisition_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Acquisition", user)


def fixed_asset_depreciation_entry_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Depreciation Entry", user)


def fixed_asset_disposal_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Disposal", user)


def fixed_asset_auto_depreciation_policy_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Auto Depreciation Policy", user)


def fixed_asset_transfer_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Transfer", user)


def fixed_asset_write_off_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Write-Off", user)


def fixed_asset_revaluation_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Revaluation", user)


def fixed_asset_maintenance_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Maintenance", user)


def fixed_asset_inspection_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Inspection", user)


def fixed_asset_movement_log_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Movement Log", user)


def fixed_asset_location_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Location", user)


def asset_meter_reading_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Meter Reading", user)


def asset_failure_event_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Failure Event", user)


def asset_condition_snapshot_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Condition Snapshot", user)


def asset_reliability_trend_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Reliability Trend", user)


def asset_alert_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Alert", user)


def asset_recommendation_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Recommendation", user)


def asset_relationship_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Relationship", user)


def asset_inspection_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Inspection", user)


def asset_risk_matrix_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Risk Matrix", user)


def asset_threshold_profile_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Threshold Profile", user)


def asset_health_rule_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Health Rule", user)


def functional_location_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Functional Location", user)


def maintenance_strategy_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Maintenance Strategy", user)


def asset_work_order_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Work Order", user)


def asset_inspection_template_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Inspection Template", user)


def hotel_property_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Hotel Property", user)


def hotel_room_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Hotel Room", user)


def hotel_functional_area_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Hotel Functional Area", user)


def rfid_scan_log_query_conditions(user=None, **kwargs):
	return _query_conditions_for("RFID Scan Log", user)


def hotel_asset_inspection_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Hotel Asset Inspection", user)


def hotel_asset_transfer_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Hotel Asset Transfer", user)
