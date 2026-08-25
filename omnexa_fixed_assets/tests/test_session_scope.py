# Copyright (c) 2026, Omnexa
from frappe.tests.utils import FrappeTestCase


class TestSessionScope(FrappeTestCase):
	def test_vertical_dashboard(self):
		from omnexa_fixed_assets.vertical_dashboard_api import get_vertical_dashboard

		out = get_vertical_dashboard()
		self.assertEqual(out.get("app"), "omnexa_fixed_assets")
		self.assertIn("uses_session_context", out)
