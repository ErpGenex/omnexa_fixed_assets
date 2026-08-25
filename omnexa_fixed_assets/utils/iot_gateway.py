# Copyright (c) 2026, Omnexa and contributors
# MIT License

"""IoT gateway ingest — validates API key and writes meter readings via queue-safe path."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, now_datetime


@frappe.whitelist(allow_guest=True)
def iot_ingest_reading(api_key: str, asset: str, meter_type: str, value: float, reading_time: str | None = None):
	"""Public IoT ingest endpoint (authenticated via site-config or Asset IoT Gateway key)."""
	_validate_api_key(api_key)

	if not asset or not frappe.db.exists("Fixed Asset", asset):
		frappe.throw(_("Unknown asset"), frappe.DoesNotExistError)

	meter_type = (meter_type or "").strip()
	if not meter_type:
		frappe.throw(_("meter_type is required"))

	if not frappe.db.exists("DocType", "Asset Meter Reading"):
		frappe.throw(_("Asset Meter Reading DocType is not installed"))

	doc = frappe.get_doc(
		{
			"doctype": "Asset Meter Reading",
			"asset": asset,
			"meter_type": meter_type,
			"value": flt(value),
			"reading_time": reading_time or now_datetime(),
			"source": "IoT Gateway",
		}
	)
	doc.insert(ignore_permissions=True)

	return {"ok": True, "reading": doc.name}


def _validate_api_key(api_key: str) -> None:
	expected = (frappe.conf.get("omnexa_iot_gateway_key") or "").strip()
	if not expected:
		expected = (frappe.db.get_single_value("Asset IoT Gateway Settings", "api_key") or "").strip()
	if not expected or (api_key or "").strip() != expected:
		frappe.throw(_("Invalid IoT gateway API key"), frappe.AuthenticationError)
