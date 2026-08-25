# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""RFID gateway/reader device authentication for bulk ingest APIs."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint


def device_auth_required() -> bool:
	return cint(frappe.conf.get("omnexa_rfid_require_device_auth")) == 1


def validate_gateway_request(gateway_id: str | None = None, api_token: str | None = None) -> str | None:
	"""Validate gateway credentials; returns gateway name or None when auth disabled."""
	if not device_auth_required():
		return None

	gateway_id = (gateway_id or "").strip()
	token = (api_token or "").strip()
	if not gateway_id or not token:
		frappe.throw(_("Gateway ID and API token are required."), frappe.AuthenticationError)

	if not frappe.db.exists("RFID Gateway", {"gateway_id": gateway_id}):
		frappe.throw(_("Unknown RFID gateway."), frappe.AuthenticationError)

	gateway = frappe.get_doc("RFID Gateway", {"gateway_id": gateway_id})
	try:
		stored = gateway.get_password("api_token") or ""
	except Exception:
		stored = ""
	if not stored:
		stored = (gateway.get("api_token") or "").strip()
	if stored != token:
		frappe.throw(_("Invalid gateway credentials."), frappe.AuthenticationError)

	_check_rate_limit(gateway_id)
	return gateway.name


def _check_rate_limit(gateway_id: str) -> None:
	limit = int(frappe.conf.get("omnexa_rfid_gateway_rate_limit") or 1200)
	cache = frappe.cache()
	key = f"omnexa_rfid_gw_rate:{gateway_id}"
	count = cint(cache.get(key) or 0) + 1
	cache.set(key, count, expires_in_sec=60)
	if count > limit:
		frappe.throw(_("Gateway rate limit exceeded."), frappe.RateLimitError)


def rotate_gateway_token(gateway_id: str) -> dict:
	"""Generate and store a new API token for a gateway."""
	import secrets

	gateway = frappe.get_doc("RFID Gateway", {"gateway_id": gateway_id})
	token = secrets.token_urlsafe(32)
	gateway.api_token = token
	gateway.token_last_rotated = frappe.utils.now_datetime()
	gateway.save(ignore_permissions=True)
	return {"ok": True, "gateway_id": gateway_id, "api_token": token}
