# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class InsuranceClaim(Document):
	def validate(self):
		if self.insurance_policy and self.company:
			pol_co = frappe.db.get_value("Insurance Policy", self.insurance_policy, "company")
			if pol_co and pol_co != self.company:
				frappe.throw(_("Company must match the selected Insurance Policy."))
