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
	return permission_query_conditions_for_branch_field(doctype, user)


def fixed_asset_category_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Category", user, **kwargs)


def fixed_asset_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset", user, **kwargs)


def fixed_asset_acquisition_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Acquisition", user, **kwargs)


def fixed_asset_depreciation_entry_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Depreciation Entry", user, **kwargs)


def fixed_asset_disposal_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Disposal", user, **kwargs)


def fixed_asset_auto_depreciation_policy_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Auto Depreciation Policy", user, **kwargs)


def fixed_asset_transfer_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Transfer", user, **kwargs)


def fixed_asset_write_off_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Write-Off", user, **kwargs)


def fixed_asset_revaluation_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Revaluation", user, **kwargs)


def fixed_asset_maintenance_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Maintenance", user, **kwargs)


def fixed_asset_inspection_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Inspection", user, **kwargs)


def fixed_asset_movement_log_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Movement Log", user, **kwargs)


def fixed_asset_location_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Fixed Asset Location", user, **kwargs)


def asset_meter_reading_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Meter Reading", user, **kwargs)


def asset_failure_event_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Failure Event", user, **kwargs)


def asset_condition_snapshot_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Condition Snapshot", user, **kwargs)


def asset_reliability_trend_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Reliability Trend", user, **kwargs)


def asset_alert_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Alert", user, **kwargs)


def asset_recommendation_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Recommendation", user, **kwargs)


def asset_relationship_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Relationship", user, **kwargs)


def asset_inspection_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Inspection", user, **kwargs)


def asset_risk_matrix_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Risk Matrix", user, **kwargs)


def asset_threshold_profile_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Threshold Profile", user, **kwargs)


def asset_health_rule_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Health Rule", user, **kwargs)


def functional_location_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Functional Location", user, **kwargs)


def maintenance_strategy_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Maintenance Strategy", user, **kwargs)


def asset_work_order_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Work Order", user, **kwargs)


def asset_inspection_template_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Asset Inspection Template", user, **kwargs)


def hotel_property_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Hotel Property", user, **kwargs)


def hotel_room_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Hotel Room", user, **kwargs)


def hotel_functional_area_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Hotel Functional Area", user, **kwargs)


def rfid_scan_log_query_conditions(user=None, **kwargs):
	return _query_conditions_for("RFID Scan Log", user, **kwargs)


def hotel_asset_inspection_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Hotel Asset Inspection", user, **kwargs)


def hotel_asset_transfer_query_conditions(user=None, **kwargs):
	return _query_conditions_for("Hotel Asset Transfer", user, **kwargs)
