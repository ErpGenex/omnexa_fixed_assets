# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class InsurancePolicy(Document):
	def validate(self):
		if self.docstatus == 0:
			self.policy_status = "Draft"
		if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(_("End Date cannot be before Start Date."))

	def before_submit(self):
		self.policy_status = "Submitted"

	def on_submit(self):
		today = getdate()
		if self.end_date and getdate(self.end_date) < today:
			self.db_set("policy_status", "Expired", update_modified=False)
		else:
			self.db_set("policy_status", "Active", update_modified=False)

	def on_cancel(self):
		self.db_set("policy_status", "Cancelled", update_modified=False)
