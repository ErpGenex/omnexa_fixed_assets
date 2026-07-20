# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

import frappe
from frappe.model.document import Document


class FunctionalLocation(Document):
	def validate(self):
		parent_path = ""
		if self.parent_location:
			parent_path = frappe.db.get_value("Functional Location", self.parent_location, "location_path") or self.parent_location
		base = self.functional_location_name or self.name
		self.location_path = f"{parent_path}/{base}".strip("/")
