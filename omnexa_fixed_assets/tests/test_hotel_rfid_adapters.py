# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from omnexa_fixed_assets.utils.rfid.factory import get_rfid_adapter


def test_rfid_adapter_factory_known_providers():
	assert get_rfid_adapter("zebra").name == "zebra"
	assert get_rfid_adapter("impinj").name == "impinj"
	assert get_rfid_adapter("chainway").name == "chainway"


def test_rfid_adapter_factory_fallback_generic():
	assert get_rfid_adapter("unknown").name == "generic"
	assert get_rfid_adapter(None).name == "generic"
