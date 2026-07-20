# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import NestedSet


class FixedAssetCategory(NestedSet):
	nsm_parent_field = "parent_fixed_asset_category"

	def validate(self):
		if self.parent_fixed_asset_category:
			parent = frappe.db.get_value(
				"Fixed Asset Category",
				self.parent_fixed_asset_category,
				"company",
			)
			if parent and parent != self.company:
				frappe.throw(_("Parent category must belong to the same company."), title=_("Company"))
		if not self.is_group:
			self._validate_leaf_gl_accounts()
			self._validate_depreciation_defaults()

	def _validate_leaf_gl_accounts(self):
		for field, label in (
			("asset_gl_account", _("Asset account")),
			("accumulated_depreciation_gl_account", _("Accumulated depreciation")),
			("depreciation_expense_gl_account", _("Depreciation expense")),
		):
			acc = self.get(field)
			if not acc:
				frappe.throw(
					_("Leaf category requires {0}.").format(label),
					title=_("GL Accounts"),
				)
			self._validate_leaf_gl_account(acc, label)

	def _validate_leaf_gl_account(self, account_name: str, label):
		row = frappe.db.get_value(
			"GL Account",
			account_name,
			["company", "is_group"],
			as_dict=True,
		)
		if not row:
			frappe.throw(_("GL Account {0} does not exist.").format(account_name), title=label)
		if row.company != self.company:
			frappe.throw(_("{0}: account must belong to the same company.").format(label), title=label)
		if row.is_group:
			frappe.throw(_("{0}: must be a leaf account.").format(label), title=label)

	def _validate_depreciation_defaults(self):
		method = (self.default_depreciation_method or "").strip()
		if method == "Straight Line" and self.default_useful_life_months and int(self.default_useful_life_months) < 1:
			frappe.throw(_("Default useful life must be at least 1 month."), title=_("IAS 16"))
		if method == "Declining Balance" and (
			not flt(self.default_declining_balance_rate) or flt(self.default_declining_balance_rate) <= 0
		):
			frappe.throw(
				_("Set a positive default declining balance annual rate %."),
				title=_("IAS 16"),
			)
		if method == "Units of Production" and (
			not self.default_total_estimated_units or int(self.default_total_estimated_units) < 1
		):
			frappe.throw(
				_("Set default total estimated units for units-of-production."),
				title=_("IAS 16"),
			)
