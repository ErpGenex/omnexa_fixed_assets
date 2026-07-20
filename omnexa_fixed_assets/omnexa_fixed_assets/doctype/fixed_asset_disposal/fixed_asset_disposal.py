# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from omnexa_fixed_assets.utils.capitalization import post_gl_journal


class FixedAssetDisposal(Document):
	def validate(self):
		self._validate_branch_company_match()
		self._snap_asset_figures()
		self._validate_accounts()
		self._validate_asset_eligible()

	def before_submit(self):
		asset = frappe.get_doc("Fixed Asset", self.fixed_asset)
		self.previous_status = asset.status

	def _validate_branch_company_match(self):
		branch_company = frappe.db.get_value("Branch", self.branch, "company")
		if not branch_company:
			frappe.throw(_("Branch {0} does not exist.").format(self.branch), title=_("Branch"))
		if branch_company != self.company:
			frappe.throw(_("Branch belongs to a different company."), title=_("Branch"))

	def _snap_asset_figures(self):
		if not self.fixed_asset:
			return
		asset = frappe.get_doc("Fixed Asset", self.fixed_asset)
		self.gross_book_value = flt(asset.acquisition_cost)
		self.accumulated_depreciation_snapshot = flt(asset.accumulated_depreciation)
		self.carrying_amount_snapshot = self.gross_book_value - self.accumulated_depreciation_snapshot

	def _validate_accounts(self):
		for field, label in (("cash_account", _("Cash / bank account")), ("gain_or_loss_account", _("Gain or loss"))):
			acc = self.get(field)
			row = frappe.db.get_value("GL Account", acc, ["company", "is_group"], as_dict=True)
			if not row or row.company != self.company:
				frappe.throw(_("{0}: invalid GL account.").format(label), title=_("GL"))
			if row.is_group:
				frappe.throw(_("{0}: must be a leaf account.").format(label), title=_("GL"))

	def _validate_asset_eligible(self):
		if not self.fixed_asset:
			return
		row = frappe.db.get_value(
			"Fixed Asset",
			self.fixed_asset,
			["company", "branch", "status", "capitalization_journal_entry", "asset_gl_account"],
			as_dict=True,
		)
		if not row:
			frappe.throw(_("Fixed Asset does not exist."), title=_("Asset"))
		if row.company != self.company or row.branch != self.branch:
			frappe.throw(_("Asset must belong to the same company and branch."), title=_("Asset"))
		if row.status == "disposed":
			frappe.throw(_("Asset is already disposed."), title=_("Asset"))
		if row.status == "draft" or not row.capitalization_journal_entry:
			frappe.throw(_("Only capitalized assets can be derecognized."), title=_("IAS 16"))
		if flt(self.gross_book_value) <= 0:
			frappe.throw(_("Asset has no gross book value to derecognize."), title=_("IAS 16"))

	def on_submit(self):
		asset = frappe.get_doc("Fixed Asset", self.fixed_asset)
		cost = flt(self.gross_book_value)
		accum = flt(self.accumulated_depreciation_snapshot)
		proceeds = flt(self.proceeds)
		gain = proceeds + accum - cost
		lines = [
			{"account": asset.accumulated_depreciation_gl_account, "debit": accum, "credit": 0},
			{"account": asset.asset_gl_account, "debit": 0, "credit": cost},
		]
		if proceeds > 0.005:
			lines.insert(1, {"account": self.cash_account, "debit": proceeds, "credit": 0})
		if gain > 0.005:
			lines.append({"account": self.gain_or_loss_account, "debit": 0, "credit": gain})
		elif gain < -0.005:
			lines.append({"account": self.gain_or_loss_account, "debit": -gain, "credit": 0})

		je = post_gl_journal(
			company=self.company,
			branch=self.branch,
			posting_date=self.disposal_date,
			reference=self.name,
			remarks=self.remarks
			or _("Derecognition {0} — {1}").format(self.name, self.fixed_asset),
			lines=lines,
		)
		self.db_set("journal_entry", je, update_modified=False)

		asset.acquisition_cost = 0
		asset.accumulated_depreciation = 0
		asset.units_depreciated_to_date = 0
		asset.depreciable_amount = 0
		asset.net_book_value = 0
		asset.last_depreciation_posting_date = None
		asset.status = "disposed"
		asset.save(ignore_permissions=True)

	def on_cancel(self):
		je_name = self.journal_entry
		if je_name:
			je = frappe.get_doc("Journal Entry", je_name)
			if je.docstatus == 1:
				je.cancel()

		asset = frappe.get_doc("Fixed Asset", self.fixed_asset)
		asset.acquisition_cost = flt(self.gross_book_value)
		asset.accumulated_depreciation = flt(self.accumulated_depreciation_snapshot)
		asset.status = self.previous_status or "in_use"
		asset.save(ignore_permissions=True)

		self.db_set("journal_entry", None, update_modified=False)
