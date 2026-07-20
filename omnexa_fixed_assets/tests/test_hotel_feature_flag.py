# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from omnexa_fixed_assets.utils.feature_flags import is_hotel_asset_management_enabled


def test_hotel_feature_flag_returns_bool():
	assert isinstance(is_hotel_asset_management_enabled(), bool)
