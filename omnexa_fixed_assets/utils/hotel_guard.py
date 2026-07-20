# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_fixed_assets.utils.feature_flags import (
	is_hotel_asset_management_enabled,
	is_hotel_vertical_active_for_company,
)


def enforce_hotel_feature_enabled():
	"""Guard hotel-only models/APIs from being used when feature is disabled."""
	override_co = getattr(frappe.flags, "omnexa_hotel_guard_company", None)
	if override_co and is_hotel_vertical_active_for_company(override_co):
		return
	if not is_hotel_asset_management_enabled():
		frappe.throw(
			_(
				"Hotel Asset Management is off: set Company Business Activity / Industry to Hotel Assets, "
				"or enable `enable_hotel_asset_management` in site config."
			)
		)
