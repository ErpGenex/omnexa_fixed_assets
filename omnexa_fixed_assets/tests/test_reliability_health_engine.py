# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

from frappe.tests.utils import FrappeTestCase

from omnexa_fixed_assets.utils.reliability_health_engine import (
	classify_health_status,
	compute_health_score,
	compute_reliability_from_window,
)


class TestReliabilityHealthEngine(FrappeTestCase):
	def test_health_classification_boundaries(self):
		self.assertEqual(classify_health_status(0), "Critical")
		self.assertEqual(classify_health_status(25), "Poor")
		self.assertEqual(classify_health_status(45), "Fair")
		self.assertEqual(classify_health_status(75), "Good")
		self.assertEqual(classify_health_status(95), "Excellent")

	def test_weighted_health_formula(self):
		score, status = compute_health_score(
			condition_score=80,
			reliability_score=60,
			maintenance_score=70,
			cost_efficiency_score=90,
			sensor_stability_score=50,
		)
		expected = (80 * 0.35) + (60 * 0.25) + (70 * 0.15) + (90 * 0.10) + (50 * 0.15)
		self.assertAlmostEqual(score, expected, places=6)
		self.assertEqual(status, classify_health_status(expected))

	def test_reliability_math_window(self):
		metrics = compute_reliability_from_window(total_failures=4, total_downtime=8.0, observed_hours=100.0)
		self.assertAlmostEqual(metrics.uptime, 92.0, places=6)
		self.assertAlmostEqual(metrics.mtbf, 23.0, places=6)
		self.assertAlmostEqual(metrics.mttr, 2.0, places=6)
		self.assertGreaterEqual(metrics.availability, 90.0)
