# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled


class RFIDReader(Document):
	def validate(self):
		enforce_hotel_feature_enabled()
		branch_company = frappe.db.get_value("Branch", self.branch, "company")
		if branch_company and branch_company != self.company:
			frappe.throw(_("Branch belongs to a different company."), title=_("Branch"))
