# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

from typing import Any

from .base import RFIDAdapter, RFIDScanPayload


class GenericRFIDAdapter(RFIDAdapter):
	name = "generic"

	def normalize_scan(self, payload: dict[str, Any]) -> RFIDScanPayload:
		tag = payload.get("rfid_tag") or payload.get("epc") or payload.get("uid")
		return RFIDScanPayload(
			asset=str(payload.get("asset") or ""),
			reader_device=payload.get("reader_device"),
			location_text=payload.get("location_text"),
			signal_strength=_to_float(payload.get("signal_strength")),
			scan_result=str(payload.get("scan_result") or "Seen"),
			rfid_tag=tag,
		)


class ZebraRFIDAdapter(GenericRFIDAdapter):
	name = "zebra"


class ImpinjRFIDAdapter(GenericRFIDAdapter):
	name = "impinj"


class ChainwayRFIDAdapter(GenericRFIDAdapter):
	name = "chainway"


def _to_float(v: Any) -> float | None:
	if v is None or v == "":
		return None
	try:
		return float(v)
	except Exception:
		return None
