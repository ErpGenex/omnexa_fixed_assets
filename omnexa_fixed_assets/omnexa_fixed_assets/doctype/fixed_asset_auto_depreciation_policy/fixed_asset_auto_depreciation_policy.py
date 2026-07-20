# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class FixedAssetAutoDepreciationPolicy(Document):
	def validate(self):
		self._validate_branch_company_match()
		self._validate_max_assets_per_run()

	def _validate_branch_company_match(self):
		if not self.branch:
			return
		branch_company = frappe.db.get_value("Branch", self.branch, "company")
		if not branch_company:
			frappe.throw(_("Branch {0} does not exist.").format(self.branch), title=_("Branch"))
		if branch_company != self.company:
			frappe.throw(_("Branch belongs to a different company."), title=_("Branch"))

	def _validate_max_assets_per_run(self):
		if not self.max_assets_per_run:
			self.max_assets_per_run = 500
		if int(self.max_assets_per_run) < 1:
			frappe.throw(_("Max assets per run must be at least 1."), title=_("Auto Depreciation"))
