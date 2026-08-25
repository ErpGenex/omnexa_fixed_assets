# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Fixed Assets portal catalog — isolated from healthcare/education verticals."""

from __future__ import annotations

import frappe
from frappe import _

from omnexa_core.omnexa_core.app_logo_registry import get_logo_url


def _portal(page: str, label_en: str, label_ar: str, icon: str, subtitle_en: str, subtitle_ar: str) -> dict:
	return {
		"id": page,
		"label_en": label_en,
		"label_ar": label_ar,
		"subtitle_en": subtitle_en,
		"subtitle_ar": subtitle_ar,
		"route": f"/app/{page}",
		"icon": icon,
		"exists": bool(frappe.db.exists("Page", page)),
	}


def get_grouped_portal_catalog(*, include_missing: int = 0) -> list[dict]:
	"""Asset-management portal groups — no healthcare/education bleed."""
	groups = [
		{
			"label_en": "Asset Dashboards",
			"label_ar": "لوحات الأصول",
			"portals": [
				_portal(
					"fa-executive-dashboard",
					"Executive Dashboard",
					"لوحة تنفيذية",
					"📊",
					"Asset KPIs & portfolio",
					"مؤشرات الأصول والمحفظة",
				),
				_portal(
					"fixed-assets-analytics-dashboard",
					"Analytics Dashboard",
					"لوحة التحليلات",
					"📈",
					"Trends & benchmarks",
					"الاتجاهات والمعايير",
				),
				_portal(
					"fa-hotel-assets-dashboard",
					"Hotel Assets Dashboard",
					"لوحة أصول الفنادق",
					"🏨",
					"Hospitality asset KPIs",
					"مؤشرات أصول الضيافة",
				),
				_portal(
					"fa-hospitality-command-center",
					"Hospitality Command Center",
					"مركز قيادة الضيافة",
					"🎯",
					"Live RFID & alerts",
					"RFID والتنبيهات المباشرة",
				),
				_portal(
					"fa-global-hospitality-portfolio",
					"Global Portfolio",
					"المحفظة العالمية",
					"🌍",
					"Multi-property rollup",
					"تجميع متعدد المنشآت",
				),
			],
		},
		{
			"label_en": "Role Desks",
			"label_ar": "مكاتب الأدوار",
			"portals": [
				_portal(
					"fixed-assets-operations-desk",
					"Operations Desk",
					"مكتب العمليات",
					"⚙️",
					"Maintenance & work orders",
					"الصيانة وأوامر العمل",
				),
				_portal(
					"fixed-assets-finance-desk",
					"Finance Desk",
					"مكتب المالية",
					"💰",
					"Depreciation & GL",
					"الإهلاك والمحاسبة",
				),
				_portal(
					"fixed-assets-customer-portal",
					"Customer Portal",
					"بوابة العميل",
					"👤",
					"External asset requests",
					"طلبات الأصول الخارجية",
				),
			],
		},
		{
			"label_en": "Field & Tracking",
			"label_ar": "الميدان والتتبع",
			"portals": [
				_portal(
					"fa-live-asset-tracking",
					"Live Asset Tracking",
					"تتبع الأصول المباشر",
					"📡",
					"RFID map & heatmap",
					"خريطة RFID والحرارة",
				),
				_portal(
					"fa-asset-scan-pwa",
					"Asset Scan PWA",
					"مسح الأصول",
					"📱",
					"Mobile RFID scan",
					"مسح RFID عبر الجوال",
				),
				_portal(
					"fa-linen-dashboard",
					"Linen Dashboard",
					"لوحة المفروشات",
					"🛏️",
					"Linen lifecycle",
					"دورة حياة المفروشات",
				),
				_portal(
					"fa-asset-wizards",
					"Asset Lifecycle Wizards",
					"معالجات دورة الحياة",
					"🧙",
					"Guided asset workflows",
					"سير عمل الأصول الموجّه",
				),
			],
		},
		{
			"label_en": "Workspace",
			"label_ar": "مساحة العمل",
			"portals": [
				{
					"id": "fixed-assets-workspace",
					"label_en": "Fixed Assets Workspace",
					"label_ar": "مساحة الأصول الثابتة",
					"subtitle_en": "Full module catalog",
					"subtitle_ar": "فهرس الوحدة الكامل",
					"route": "/app/fixed-assets",
					"icon": "📁",
					"exists": bool(frappe.db.exists("Workspace", "Fixed Assets")),
				},
			],
		},
	]

	if not include_missing:
		for group in groups:
			group["portals"] = [p for p in group.get("portals") or [] if p.get("exists")]
		groups = [g for g in groups if g.get("portals")]
	return groups


def get_sidebar_links() -> list[dict]:
	return [
		{
			"label_en": "Workcenter",
			"label_ar": "مركز العمل",
			"route": "/app/fixed-assets-workcenter",
			"icon": "🏢",
		},
		{
			"label_en": "Fixed Assets Workspace",
			"label_ar": "مساحة الأصول",
			"route": "/app/fixed-assets",
			"icon": "📁",
		},
		{
			"label_en": "Hotel Assets Dashboard",
			"label_ar": "لوحة الفنادق",
			"route": "/app/fa-hotel-assets-dashboard",
			"icon": "🏨",
		},
		{
			"label_en": "Asset Wizards",
			"label_ar": "معالجات الأصول",
			"route": "/app/fa-asset-wizards",
			"icon": "🧙",
		},
	]


@frappe.whitelist()
def get_workcenter_context() -> dict:
	company = frappe.defaults.get_user_default("Company") or ""
	branch = frappe.defaults.get_user_default("Branch") or ""
	groups = get_grouped_portal_catalog(include_missing=0)
	kpis = []
	try:
		from omnexa_fixed_assets import api as fa_api

		payload = fa_api.get_asset_command_center(company=company, branch=branch) if company else {}
		if isinstance(payload, dict) and payload.get("ok"):
			h = payload.get("hospitality") or {}
			kpis = [
				{"label_en": "Total Assets", "label_ar": "إجمالي الأصول", "value": h.get("total_assets") or payload.get("total_assets") or 0},
				{"label_en": "RFID Online", "label_ar": "RFID متصل", "value": h.get("rfid_online") or 0},
				{"label_en": "Missing Assets", "label_ar": "أصول مفقودة", "value": h.get("missing_assets") or 0},
				{"label_en": "Maintenance", "label_ar": "تحت الصيانة", "value": h.get("maintenance_assets") or 0},
			]
	except Exception:
		pass

	return {
		"app": "omnexa_fixed_assets",
		"title_en": "Fixed Assets",
		"title_ar": "الأصول الثابتة",
		"logo_url": get_logo_url("omnexa_fixed_assets"),
		"grouped_portals": groups,
		"sidebar": get_sidebar_links(),
		"company": company,
		"branch": branch,
		"kpis": kpis,
		"workcenter_route": "/app/fixed-assets-workcenter",
	}
