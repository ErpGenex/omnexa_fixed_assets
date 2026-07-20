from frappe.tests.utils import FrappeTestCase

from omnexa_fixed_assets import hooks


class TestFixedAssetsLicenseSmoke(FrappeTestCase):
	def test_fixed_assets_has_no_license_gate_hook(self):
		self.assertFalse(hasattr(hooks, "before_request"))
