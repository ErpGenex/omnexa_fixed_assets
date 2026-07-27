# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe

from omnexa_core.omnexa_core.feature_flags import is_feature_enabled
from omnexa_core.omnexa_core.company_activity_utils import company_activity_fields, first_company_activity_value

# Must match Option rows on Company business_activity / industry_sector / production_demo_activity.
HOTEL_ASSETS_ACTIVITY_OPTION = "Hotel Assets (إدارة أصول الفنادق)"


def company_has_hotel_assets_activity(company_name: str | None) -> bool:
	if not company_name:
		return False
	return first_company_activity_value(company_name) == HOTEL_ASSETS_ACTIVITY_OPTION


def site_has_any_hotel_assets_company() -> bool:
	"""Hotel vertical is active for the site when enabled in site_config OR any Company selects the Hotel Assets activity."""
	if is_feature_enabled("enable_hotel_asset_management", default=False):
		return True
	h = HOTEL_ASSETS_ACTIVITY_OPTION
	fields = company_activity_fields()
	if not fields:
		return False
	conditions = " OR ".join(f"`{field}` = %(m)s" for field in fields)
	row = frappe.db.sql(
		f"""
		SELECT name FROM `tabCompany`
		WHERE {conditions}
		LIMIT 1
		""",
		{"m": h
	},
	)
	return bool(row)


def is_health_engine_enabled() -> bool:
	return is_feature_enabled("enable_health_engine", default=False)


def is_condition_monitoring_enabled() -> bool:
	return is_feature_enabled("enable_condition_monitoring", default=False)


def is_reliability_enabled() -> bool:
	return is_feature_enabled("enable_reliability", default=False)


def is_failure_intelligence_enabled() -> bool:
	return is_feature_enabled("enable_failure_intelligence", default=False)


def is_predictive_rules_enabled() -> bool:
	return is_feature_enabled("enable_predictive_rules", default=False)


def is_scheduler_enabled() -> bool:
	return is_feature_enabled("enable_scheduler", default=True)


def is_inspections_enabled() -> bool:
	return is_feature_enabled("enable_inspections", default=False)


def is_hotel_vertical_active_for_company(company_name: str | None) -> bool:
	"""Hotel vertical applies to this Company row (site flag OR Company activity fields)."""
	if not company_name:
		return False
	if is_feature_enabled("enable_hotel_asset_management", default=False):
		return True
	return company_has_hotel_assets_activity(company_name)


def is_hotel_asset_management_enabled() -> bool:
	"""Hotel UI/API layer for the current session when site flag is on OR default company is Hotel Assets."""
	if is_feature_enabled("enable_hotel_asset_management", default=False):
		return True
	try:
		from omnexa_core.omnexa_core.branch_access import get_default_company
	except Exception:
		return False
	co = get_default_company()
	return company_has_hotel_assets_activity(co)
