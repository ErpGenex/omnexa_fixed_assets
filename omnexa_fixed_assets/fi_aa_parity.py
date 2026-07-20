# Copyright (c) 2026, ErpGenEx
"""FI-AA SAP parity helpers."""

from __future__ import annotations

from frappe.utils import flt


def preview_impairment_adjustment(
	carrying_amount: float,
	recoverable_amount: float,
	*,
	asset_name: str | None = None,
) -> dict:
	"""IAS 36 impairment loss preview (no GL posting)."""
	carrying = flt(carrying_amount)
	recoverable = flt(recoverable_amount)
	loss = max(0.0, carrying - recoverable)
	return {
		"asset": asset_name,
		"carrying_amount": carrying,
		"recoverable_amount": recoverable,
		"impairment_loss": loss,
		"requires_posting": loss > 0,
		"sap_module": "FI-AA"
	}
