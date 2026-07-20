# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

from .base import RFIDAdapter
from .providers import ChainwayRFIDAdapter, GenericRFIDAdapter, ImpinjRFIDAdapter, ZebraRFIDAdapter


def get_rfid_adapter(provider: str | None) -> RFIDAdapter:
	key = (provider or "generic").strip().lower()
	if key == "zebra":
		return ZebraRFIDAdapter()
	if key == "impinj":
		return ImpinjRFIDAdapter()
	if key == "chainway":
		return ChainwayRFIDAdapter()
	return GenericRFIDAdapter()
