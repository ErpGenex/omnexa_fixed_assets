# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from omnexa_fixed_assets.utils.capitalization import post_gl_journal
from omnexa_fixed_assets.utils.ias16 import remaining_depreciable, suggest_monthly_depreciation


class FixedAssetDepreciationEntry(Document):
	def validate(self):
		self._validate_branch_company_match()
		self._validate_asset_eligible()
		self._set_suggestion()
		self._validate_amount_and_dates()

	def _validate_branch_company_match(self):
		branch_company = frappe.db.get_value("Branch", self.branch, "company")
		if not branch_company:
			frappe.throw(_("Branch {0} does not exist.").format(self.branch), title=_("Branch"))
		if branch_company != self.company:
			frappe.throw(_("Branch belongs to a different company."), title=_("Branch"))

	def _validate_asset_eligible(self):
		row = frappe.db.get_value(
			"Fixed Asset",
			self.fixed_asset,
			[
				"company",
				"branch",
				"status",
				"measurement_model",
				"depreciation_method",
				"capitalization_journal_entry",
			],
			as_dict=True,
		)
		if not row:
			frappe.throw(_("Fixed Asset does not exist."), title=_("Asset"))
		if row.company != self.company or row.branch != self.branch:
			frappe.throw(_("Asset must belong to the same company and branch."), title=_("Asset"))
		if row.status in ("draft", "disposed"):
			frappe.throw(_("Cannot post depreciation for this asset status."), title=_("Asset"))
		if not row.capitalization_journal_entry:
			frappe.throw(_("Capitalize the asset before depreciation."), title=_("Asset"))
		if row.measurement_model != "Cost Model":
			frappe.throw(_("Automated depreciation entries support cost model only."), title=_("IAS 16"))
		if not row.depreciation_method or row.depreciation_method in ("", "None"):
			frappe.throw(_("Set a depreciation method on the asset."), title=_("IAS 16"))

	def _set_suggestion(self):
		asset = frappe.get_doc("Fixed Asset", self.fixed_asset)
		units = int(self.units_produced or 0) if (asset.depreciation_method or "") == "Units of Production" else None
		self.suggested_depreciation = suggest_monthly_depreciation(
			method=asset.depreciation_method or "",
			cost=flt(asset.acquisition_cost),
			salvage=flt(asset.salvage_value),
			accumulated_depreciation=flt(asset.accumulated_depreciation),
			useful_life_months=asset.useful_life_months,
			annual_declining_rate_percent=flt(asset.declining_balance_rate_annual),
			total_estimated_units=asset.total_estimated_units,
			units_this_period=units,
		)

	def _validate_amount_and_dates(self):
		amt = flt(self.depreciation_amount)
		if amt <= 0:
			frappe.throw(_("Depreciation amount must be positive."), title=_("Depreciation"))
		asset = frappe.get_doc("Fixed Asset", self.fixed_asset)
		rem = remaining_depreciable(
			asset.acquisition_cost, asset.salvage_value, asset.accumulated_depreciation
		)
		if amt - rem > 0.02:
			frappe.throw(
				_("Amount exceeds remaining depreciable balance ({0}).").format(rem),
				title=_("IAS 16"),
			)
		if asset.depreciation_start_date and getdate(self.posting_date) < getdate(
			asset.depreciation_start_date
		):
			frappe.throw(
				_("Posting date cannot be before depreciation start date on the asset."),
				title=_("IAS 16"),
			)

	def on_submit(self):
		asset = frappe.get_doc("Fixed Asset", self.fixed_asset)
		amt = flt(self.depreciation_amount)
		je = post_gl_journal(
			company=self.company,
			branch=self.branch,
			posting_date=self.posting_date,
			reference=self.name,
			remarks=self.remarks
			or _("Depreciation {0} — {1}").format(self.name, self.fixed_asset),
			lines=[
				{"account": asset.depreciation_expense_gl_account, "debit": amt, "credit": 0
	},
				{"account": asset.accumulated_depreciation_gl_account, "debit": 0, "credit": amt
	},
			],
		)
		self.db_set("journal_entry", je, update_modified=False)

		asset.accumulated_depreciation = flt(asset.accumulated_depreciation) + amt
		if (asset.depreciation_method or "") == "Units of Production" and int(self.units_produced or 0) > 0:
			asset.units_depreciated_to_date = int(asset.units_depreciated_to_date or 0) + int(
				self.units_produced
			)
		asset.last_depreciation_posting_date = self.posting_date
		asset.save(ignore_permissions=True)

	def on_cancel(self):
		je_name = self.journal_entry
		if je_name:
			je = frappe.get_doc("Journal Entry", je_name)
			if je.docstatus == 1:
				je.cancel()

		asset = frappe.get_doc("Fixed Asset", self.fixed_asset)
		amt = flt(self.depreciation_amount)
		asset.accumulated_depreciation = max(0.0, flt(asset.accumulated_depreciation) - amt)
		if (asset.depreciation_method or "") == "Units of Production" and int(self.units_produced or 0) > 0:
			asset.units_depreciated_to_date = max(
				0, int(asset.units_depreciated_to_date or 0) - int(self.units_produced)
			)
		prev_date = frappe.db.sql(
			"""
			SELECT MAX(posting_date) FROM `tabFixed Asset Depreciation Entry`
			WHERE docstatus = 1 AND fixed_asset = %s AND name != %s
			""",
			(asset.name, self.name),
		)
		asset.last_depreciation_posting_date = prev_date[0][0] if prev_date and prev_date[0][0] else None
		if asset.status == "fully_depreciated" and remaining_depreciable(
			asset.acquisition_cost, asset.salvage_value, asset.accumulated_depreciation
		) > 0.02:
			asset.status = "in_use"
		asset.save(ignore_permissions=True)
		self.db_set("journal_entry", None, update_modified=False)
