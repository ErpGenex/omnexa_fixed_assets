# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled


class LinenItem(Document):
	def validate(self):
		enforce_hotel_feature_enabled()
		self._validate_rfid_uniqueness()
		self._validate_branch_company()

	def _validate_branch_company(self):
		branch_company = frappe.db.get_value("Branch", self.branch, "company")
		if branch_company and branch_company != self.company:
			frappe.throw(_("Branch belongs to a different company."), title=_("Branch"))

	def _validate_rfid_uniqueness(self):
		tag = (self.rfid_tag or "").strip()
		if not tag:
			return
		existing = frappe.db.get_value(
			"Linen Item",
			{"rfid_tag": tag, "name": ["!=", self.name or ""]},
			"name",
		)
		if existing:
			frappe.throw(_("RFID Tag must be unique. Existing linen: {0}").format(existing))

		asset = frappe.db.get_value("Fixed Asset", {"rfid_tag": tag}, "name")
		if asset:
			frappe.throw(_("RFID Tag already assigned to Fixed Asset {0}").format(asset))

	def remaining_wash_cycles(self) -> int:
		return max(int(self.expected_life_cycles or 0) - int(self.wash_count or 0), 0)

	def needs_replacement_warning(self) -> bool:
		remaining = self.remaining_wash_cycles()
		threshold = int(frappe.conf.get("omnexa_linen_replacement_threshold") or 15)
		return remaining <= threshold
