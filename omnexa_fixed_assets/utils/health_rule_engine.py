# Copyright (c) 2026, Omnexa and contributors
# MIT License

"""Evaluate Asset Health Rule rows against asset metrics."""

from __future__ import annotations

import re

import frappe
from frappe.utils import flt

from omnexa_fixed_assets.utils.predictive_wo import create_predictive_work_order


def _asset_context(asset) -> dict:
	return {
		"health_score": flt(asset.health_score),
		"risk_score": flt(asset.risk_score),
		"failure_frequency": flt(asset.failure_frequency),
		"degradation_index": flt(asset.degradation_index),
		"availability": flt(asset.availability),
		"mtbf": flt(asset.mtbf),
		"mttr": flt(asset.mttr),
		"reliability_score": flt(asset.reliability_score),
	}


def evaluate_condition(expression: str, ctx: dict) -> bool:
	expr = (expression or "").strip()
	if not expr:
		return False
	safe = expr
	for key in sorted(ctx.keys(), key=len, reverse=True):
		safe = re.sub(rf"\b{re.escape(key)}\b", str(flt(ctx[key])), safe)
	if not re.match(r"^[\d.\s<>=!&|()+*/-]+$", safe):
		return False
	try:
		return bool(eval(safe, {"__builtins__": {}}, {}))  # noqa: S307 — admin-configured numeric expressions only
	except Exception:
		return False


def evaluate_asset_health_rules(asset_name: str) -> dict:
	if not frappe.db.exists("DocType", "Asset Health Rule"):
		return {"ok": True, "actions": []}

	asset = frappe.get_doc("Fixed Asset", asset_name)
	ctx = _asset_context(asset)
	filters = {"enabled": 1, "company": asset.company}
	if asset.branch:
		filters["branch"] = ["in", [asset.branch, ""]]

	rules = frappe.get_all(
		"Asset Health Rule",
		filters=filters,
		fields=["name", "condition_expression", "action_type", "action_payload"],
		limit_page_length=100,
	)

	actions = []
	for rule in rules:
		if not evaluate_condition(rule.condition_expression, ctx):
			continue

		action = rule.action_type
		payload = (rule.action_payload or "").strip()

		if action == "Create Alert":
			alert = frappe.get_doc(
				{
					"doctype": "Asset Alert",
					"asset": asset.name,
					"company": asset.company,
					"branch": asset.branch,
					"alert_type": "Health Rule",
					"severity": "High",
					"status": "Open",
					"message": payload or f"Health rule {rule.name} triggered",
				}
			)
			alert.insert(ignore_permissions=True)
			actions.append({"rule": rule.name, "action": "alert", "name": alert.name})

		elif action == "Create Work Order":
			result = create_predictive_work_order(
				asset.name,
				payload or f"Health rule {rule.name} triggered",
				priority="High",
				source=f"health_rule:{rule.name}",
			)
			if result.get("ok"):
				actions.append({"rule": rule.name, "action": "work_order", **result})

		elif action == "Create Inspection" and frappe.db.exists("DocType", "Asset Inspection"):
			insp = frappe.get_doc(
				{
					"doctype": "Asset Inspection",
					"asset": asset.name,
					"company": asset.company,
					"branch": asset.branch,
					"inspection_type": "Condition",
					"status": "Draft",
					"notes": payload or f"Health rule {rule.name}",
				}
			)
			insp.insert(ignore_permissions=True)
			actions.append({"rule": rule.name, "action": "inspection", "name": insp.name})

	return {"ok": True, "asset": asset_name, "actions": actions}
