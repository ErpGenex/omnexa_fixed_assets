import frappe
from frappe.tests.utils import FrappeTestCase

from omnexa_fixed_assets.utils.health_formula import degradation_from_condition_state, get_health_weights


class TestHealthFormula(FrappeTestCase):
	def test_degradation_mapping(self):
		self.assertEqual(degradation_from_condition_state("Critical"), 90.0)
		self.assertEqual(degradation_from_condition_state("Normal"), 0.0)

	def test_weights_normalize(self):
		weights = get_health_weights()
		self.assertIn("weight_condition", weights)
		total = sum(weights.values())
		self.assertAlmostEqual(total, 1.0, places=2)


class TestHealthRuleEngine(FrappeTestCase):
	def test_evaluate_condition(self):
		from omnexa_fixed_assets.utils.health_rule_engine import evaluate_condition

		ctx = {"health_score": 35, "risk_score": 65}
		self.assertTrue(evaluate_condition("health_score < 40", ctx))
		self.assertFalse(evaluate_condition("health_score > 80", ctx))
