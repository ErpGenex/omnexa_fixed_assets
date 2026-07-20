# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime


class AssetWorkOrder(Document):
	def validate(self):
		if self.planned_start and self.planned_end and get_datetime(self.planned_end) < get_datetime(self.planned_start):
			frappe.throw(_("Planned End cannot be before Planned Start."), title=_("Asset Work Order"))
		if self.status == "Completed" and not self.completion_date:
			self.completion_date = get_datetime()

	def on_submit(self):
		if self.status in ("Draft", "Planned"):
			self.status = "Assigned" if self.assigned_to else "Planned"

	def on_cancel(self):
		self.status = "Cancelled"
