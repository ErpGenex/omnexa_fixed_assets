# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled
from omnexa_fixed_assets.utils.linen.lifecycle import apply_laundry_cycle


class LinenLaundryCycle(Document):
	def validate(self):
		enforce_hotel_feature_enabled()

	def on_submit(self):
		apply_laundry_cycle(self)

	def before_save(self):
		if not self.cycle_number:
			self.cycle_number = frappe.db.count("Linen Laundry Cycle", {"linen_item": self.linen_item}) + 1
