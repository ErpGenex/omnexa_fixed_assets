# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RFIDScanPayload:
	asset: str
	reader_device: str | None = None
	location_text: str | None = None
	signal_strength: float | None = None
	scan_result: str = "Seen"
	rfid_tag: str | None = None


class RFIDAdapter:
	"""Provider adapter interface for RFID integrations."""

	name = "base"

	def normalize_scan(self, payload: dict[str, Any]) -> RFIDScanPayload:
		raise NotImplementedError
