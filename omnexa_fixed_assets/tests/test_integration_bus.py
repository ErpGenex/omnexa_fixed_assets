# Copyright (c) 2026, ErpGenEx
# License: MIT

"""Wave 8 — omnexa_fixed_assets integration with financial core via integration bus."""

import frappe
from frappe.tests.utils import FrappeTestCase

from omnexa_core.omnexa_core.integration_bridge import financial_snapshot, inventory_snapshot


class TestIntegrationBus(FrappeTestCase):
	app_name = "omnexa_fixed_assets"

	def test_financial_snapshot_via_bus(self):
		company = frappe.db.get_value("Company", {}, "name")
		if not company:
			self.skipTest("no company")
		out = financial_snapshot(company, source_app=self.app_name)
		self.assertTrue(out.ok, msg=out.message)
		self.assertEqual(out.data.get("company"), company)

	def test_inventory_snapshot_via_bus(self):
		company = frappe.db.get_value("Company", {}, "name")
		if not company:
			self.skipTest("no company")
		out = inventory_snapshot(company, source_app=self.app_name)
		self.assertTrue(out.ok, msg=out.message)
