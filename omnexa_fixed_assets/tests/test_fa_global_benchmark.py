# Copyright (c) 2026, Omnexa
import json, frappe
from frappe.tests.utils import FrappeTestCase
from omnexa_fixed_assets.fa_gap_register import GLOBAL_LEADER_TARGET, get_gap_status
from omnexa_fixed_assets.fa_global_benchmark import get_global_fa_score
from omnexa_fixed_assets.workspace.fa_workspace import sync_fa_workspace_menu

class TestFaGlobalBenchmark(FrappeTestCase):
	def test_global_score(self):
		s = get_global_fa_score()
		self.assertGreaterEqual(s["weighted_score"], GLOBAL_LEADER_TARGET)
		self.assertTrue(s.get("global_leader_gate"))
	def test_gaps_closed(self):
		self.assertTrue(get_gap_status()["global_leader_gate"])
	def test_workspace_sync(self):
		stats = sync_fa_workspace_menu(save=True, rebuild=True)
		self.assertGreater(stats["total_links"], 10)
		ws = frappe.get_doc("Workspace", "Fixed Assets")
		self.assertGreater(len(ws.shortcuts), 5)
