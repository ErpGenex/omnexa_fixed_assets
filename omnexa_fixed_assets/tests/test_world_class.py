# Copyright (c) 2026, Omnexa
from frappe.tests.utils import FrappeTestCase

from omnexa_core.omnexa_core.tests.world_class_functional_mixin import WorldClassFunctionalTestMixin


class TestWorldClassCertification(FrappeTestCase, WorldClassFunctionalTestMixin):
	app_name = "omnexa_fixed_assets"

	def test_world_class_certification(self):
		self.assert_world_class_certification()

	def test_vertical_dashboard_world_class(self):
		self.assert_vertical_dashboard_certified()
