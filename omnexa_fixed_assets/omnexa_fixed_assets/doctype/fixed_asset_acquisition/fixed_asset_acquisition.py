# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from omnexa_fixed_assets.utils.capitalization import post_capitalization_journal_entry


class FixedAssetAcquisition(Document):
	def validate(self):
		self._validate_branch_company_match()
		self._validate_asset()
		self._validate_credit_account()
		self._validate_distinct_accounts()
		if flt(self.capitalization_amount) <= 0:
			frappe.throw(_("Capitalization amount must be positive."), title=_("Amount"))

	def _validate_branch_company_match(self):
		branch_company = frappe.db.get_value("Branch", self.branch, "company")
		if not branch_company:
			frappe.throw(_("Branch {0} does not exist.").format(self.branch), title=_("Branch"))
		if branch_company != self.company:
			frappe.throw(_("Branch belongs to a different company."), title=_("Branch"))

	def _validate_asset(self):
		row = frappe.db.get_value(
			"Fixed Asset",
			self.fixed_asset,
			["company", "branch", "capitalization_journal_entry", "status"],
			as_dict=True,
		)
		if not row:
			frappe.throw(_("Fixed Asset does not exist."), title=_("Asset"))
		if row.company != self.company or row.branch != self.branch:
			frappe.throw(_("Asset must belong to the same company and branch."), title=_("Asset"))
		if row.capitalization_journal_entry:
			frappe.throw(_("This asset is already capitalized."), title=_("Asset"))
		if row.status == "disposed":
			frappe.throw(_("Cannot capitalize a disposed asset."), title=_("Asset"))

	def _validate_credit_account(self):
		row = frappe.db.get_value(
			"GL Account",
			self.credit_account,
			["company", "is_group"],
			as_dict=True,
		)
		if not row or row.company != self.company:
			frappe.throw(_("Credit account must be a leaf GL account for this company."), title=_("GL"))
		if row.is_group:
			frappe.throw(_("Credit account must be a leaf account."), title=_("GL"))

	def _validate_distinct_accounts(self):
		asset_gl = frappe.db.get_value("Fixed Asset", self.fixed_asset, "asset_gl_account")
		if asset_gl and self.credit_account == asset_gl:
			frappe.throw(_("Credit account cannot be the same as the asset GL account."), title=_("GL"))

	def on_submit(self):
		asset = frappe.get_doc("Fixed Asset", self.fixed_asset)
		je_name = post_capitalization_journal_entry(
			company=self.company,
			branch=self.branch,
			posting_date=self.posting_date,
			debit_account=asset.asset_gl_account,
			credit_account=self.credit_account,
			amount=flt(self.capitalization_amount),
			reference=self.name,
			remarks=self.remarks
			or _("Fixed asset acquisition {0} — {1}").format(self.name, self.fixed_asset),
		)
		self.db_set("journal_entry", je_name, update_modified=False)

		asset.acquisition_cost = flt(self.capitalization_amount)
		asset.capitalization_date = self.posting_date
		asset.capitalization_journal_entry = je_name
		asset.status = "acquired"
		if not asset.depreciation_start_date:
			asset.depreciation_start_date = self.posting_date
		asset.save(ignore_permissions=True)

	def on_cancel(self):
		je_name = self.journal_entry
		if je_name:
			je = frappe.get_doc("Journal Entry", je_name)
			if je.docstatus == 1:
				je.cancel()

		asset = frappe.get_doc("Fixed Asset", self.fixed_asset)
		if asset.capitalization_journal_entry == je_name:
			asset.capitalization_journal_entry = None
			asset.acquisition_cost = 0
			asset.capitalization_date = None
			asset.depreciation_start_date = None
			asset.status = "draft"
			asset.save(ignore_permissions=True)

		self.db_set("journal_entry", None, update_modified=False)
