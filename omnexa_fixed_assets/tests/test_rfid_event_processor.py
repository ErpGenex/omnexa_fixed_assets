# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from omnexa_fixed_assets.utils.rfid.event_processor import resolve_asset_from_identifiers
from omnexa_fixed_assets.utils.rfid.factory import get_rfid_adapter


def test_resolve_asset_prefers_explicit_name():
	assert resolve_asset_from_identifiers("FA-001", "TAG-001") == "FA-001"


def test_rfid_adapter_accepts_epc_alias():
	payload = get_rfid_adapter("zebra").normalize_scan(
		{"epc": "E280116060000204", "reader_device": "R1", "location_text": "Lobby"}
	)
	assert payload.rfid_tag == "E280116060000204"


def test_rfid_adapter_scan_payload_fields():
	payload = get_rfid_adapter(None).normalize_scan(
		{"asset": "A-1", "reader_device": "R1", "location_text": "Floor 2", "signal_strength": 80}
	)
	assert payload.asset == "A-1"
	assert payload.reader_device == "R1"
	assert payload.scan_result == "Seen"
