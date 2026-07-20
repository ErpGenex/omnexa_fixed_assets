# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class FixedAssetRevaluation(Document):
	def validate(self):
		self._validate_measurement_model()
		self._validate_amounts()

	def on_submit(self):
		self._apply_revaluation_to_asset()

	def on_cancel(self):
		self._revert_revaluation_on_asset()

	def _validate_measurement_model(self):
		model = frappe.db.get_value("Fixed Asset", self.fixed_asset, "measurement_model") or "Cost"
		if model == "Cost" and not frappe.flags.get("allow_cost_model_revaluation"):
			frappe.msgprint(
				_("Asset uses cost model; revaluation is optional under IAS 16 revaluation model."),
				indicator="orange",
			)

	def _validate_amounts(self):
		if flt(self.revalued_amount) <= 0:
			frappe.throw(_("Revalued Amount must be positive"))
		nbv = flt(frappe.db.get_value("Fixed Asset", self.fixed_asset, "net_book_value"))
		if nbv and abs(flt(self.revalued_amount) - nbv) < 0.01:
			frappe.msgprint(_("Revalued amount is close to current net book value."), indicator="blue")

	def _apply_revaluation_to_asset(self):
		asset = frappe.get_doc("Fixed Asset", self.fixed_asset)
		previous_nbv = flt(asset.net_book_value) or flt(asset.acquisition_cost)
		surplus = flt(self.revalued_amount) - previous_nbv
		asset.net_book_value = flt(self.revalued_amount)
		if flt(asset.acquisition_cost) < flt(self.revalued_amount):
			asset.acquisition_cost = flt(self.revalued_amount)
		asset.flags.ignore_validate = True
		asset.save(ignore_permissions=True)
		log_platform = _safe_audit_log(self, previous_nbv, surplus)

	def _revert_revaluation_on_asset(self):
		# Non-destructive cancel: only log; manual asset correction if needed
		_safe_audit_log(self, None, None, action="cancel")


def _safe_audit_log(doc, previous_nbv, surplus, action: str = "submit"):
	try:
		from omnexa_core.omnexa_core.platform_audit import log_platform_event

		log_platform_event(
			"fixed_asset.revaluation",
			doc.doctype,
			doc.name,
			action=action,
			company=doc.company,
			branch=doc.branch,
			ledger_domain="Accounting",
			payload={
				"fixed_asset": doc.fixed_asset,
				"revalued_amount": flt(doc.revalued_amount),
				"previous_nbv": previous_nbv,
				"surplus": surplus
	},
			amount=flt(doc.revalued_amount),
		)
	except Exception:
		pass
