# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe.model.document import Document

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled


class LinenMovement(Document):
	def validate(self):
		enforce_hotel_feature_enabled()
