/* global frappe */
frappe.provide("omnexa_fixed_assets.hotel_portal");

(function () {
	"use strict";

	function t(ar, en) {
		return frappe.boot.lang === "ar" ? ar : en;
	}

	function navigateRoute(route) {
		if (!route) return;
		if (route.startsWith("/app/query-report/")) {
			const name = decodeURIComponent(route.replace("/app/query-report/", ""));
			frappe.set_route("query-report", name);
			return;
		}
		const newForm = route.match(/^\/app\/([a-z0-9-]+)\/new$/);
		if (newForm) {
			frappe.set_route(`${newForm[1]}/new`);
			return;
		}
		if (route.startsWith("/app/") && !route.includes("/List/")) {
			const slug = route.replace(/^\/app\//, "").replace(/\/$/, "");
			if (slug) {
				frappe.set_route(slug);
				return;
			}
		}
		if (route.startsWith("/app/") || route.startsWith("/education/")) {
			window.location.href = route;
			return;
		}
		frappe.set_route(route);
	}

	function renderSidebar(portals, activeRoute) {
		const $nav = $('<nav class="oj-vertical-portal-sidebar"></nav>');
		(portals || []).forEach((p) => {
			const label = t(p.label_ar, p.label_en);
			const active = p.route === activeRoute ? " active" : "";
			const $link = $(`
				<a class="oj-sidebar-link${active}" href="${frappe.utils.escape_html(p.route)}">
					<span class="oj-sidebar-icon">${p.icon || "🌐"}</span>
					<span>${frappe.utils.escape_html(label)}</span>
				</a>`);
			$link.on("click", (e) => {
				e.preventDefault();
				navigateRoute(p.route);
			});
			$nav.append($link);
		});
		return $nav;
	}

	function renderOperationalMenu(sections) {
		const $menu = $('<div class="oj-pharma-ops-menu"></div>');
		(sections || []).forEach((section) => {
			const title = t(section.title_ar, section.title_en);
			$menu.append(`<div class="oj-sidebar-section">${frappe.utils.escape_html(title)}</div>`);
			(section.items || []).forEach((item) => {
				const label = t(item.label_ar, item.label_en);
				const $btn = $(`
					<a class="oj-pharma-ops-link" href="${frappe.utils.escape_html(item.route)}">
						${(window.omnexa_core && omnexa_core.vertical_portal && omnexa_core.vertical_portal.renderPortalIcon)
							? omnexa_core.vertical_portal.renderPortalIcon(item, "oj-sidebar-icon")
							: `<span class="oj-sidebar-icon">${frappe.utils.escape_html(item.icon || "▫️")}</span>`}
						<span>${frappe.utils.escape_html(label)}</span>
					</a>`);
				$btn.on("click", (e) => {
					e.preventDefault();
					navigateRoute(item.route);
				});
				$menu.append($btn);
			});
		});
		return $menu;
	}

	function renderQuickActions(actions) {
		const $row = $('<div class="omnexa-portal-quick-actions"></div>');
		(actions || []).forEach((act) => {
			const label = t(act.label_ar, act.label_en);
			const $btn = $(`
				<a class="btn btn-sm btn-default omnexa-portal-quick-btn" href="${frappe.utils.escape_html(act.route)}">
					${act.icon || "⚡"} ${frappe.utils.escape_html(label)}
				</a>`);
			$btn.on("click", (e) => {
				e.preventDefault();
				navigateRoute(act.route);
			});
			$row.append($btn);
		});
		return $row;
	}

	function renderListPanel(titleAr, titleEn, rows) {
		const title = t(titleAr, titleEn);
		const $panel = $(`<div class="omnexa-portal-panel"><h5>${frappe.utils.escape_html(title)}</h5></div>`);
		const $list = $('<ul class="omnexa-portal-list"></ul>');
		if (!rows || !rows.length) {
			$list.append(`<li class="text-muted">${t("لا توجد عناصر", "No items")}</li>`);
		} else {
			rows.forEach((row) => {
				const label = row.description || row.name || "-";
				$list.append(`<li>${frappe.utils.escape_html(String(label))}</li>`);
			});
		}
		$panel.append($list);
		return $panel;
	}

	function renderBreakdownTable(titleAr, titleEn, rows, labelKey, countKey) {
		const title = t(titleAr, titleEn);
		const $panel = $(`<div class="omnexa-portal-panel"><h5>${frappe.utils.escape_html(title)}</h5></div>`);
		const $table = $('<table class="table table-sm" style="margin:0"></table>');
		const $body = $("<tbody></tbody>");
		if (!rows || !rows.length) {
			$body.append(`<tr><td class="text-muted">${t("لا توجد بيانات", "No data")}</td></tr>`);
		} else {
			rows.forEach((row) => {
				const label = row[labelKey] || row.name || "-";
				const count = row[countKey] ?? 0;
				$body.append(
					`<tr><td>${frappe.utils.escape_html(String(label))}</td><td class="text-right">${frappe.utils.escape_html(String(count))}</td></tr>`
				);
			});
		}
		$table.append($body);
		$panel.append($table);
		return $panel;
	}

	function renderDashboard(dashboard) {
		const $dash = $('<div class="omnexa-pharma-dashboard"></div>');
		if (!dashboard) return $dash;

		const kpis = dashboard.kpis || [];
		if (kpis.length) {
			const $kpis = $('<div class="omnexa-portal-kpi-grid"></div>');
			kpis.forEach((kpi) => {
				const title = t(kpi.title_ar, kpi.title_en || kpi.title);
				$kpis.append(`
					<div class="omnexa-portal-kpi-card">
						<div class="omnexa-portal-kpi-title">${kpi.icon || "📊"} ${frappe.utils.escape_html(title)}</div>
						<div class="omnexa-portal-kpi-value">${frappe.utils.escape_html(String(kpi.value ?? 0))}</div>
					</div>`);
			});
			$dash.append($kpis);
		}

		if (dashboard.quick_actions && dashboard.quick_actions.length) {
			$dash.append(`<h5 class="oj-section-title">${t("إجراءات سريعة", "Quick Actions")}</h5>`);
			$dash.append(renderQuickActions(dashboard.quick_actions));
		}

		const $panels = $('<div class="omnexa-portal-panels"></div>');
		$panels.append(renderListPanel("قائمة العمل", "Work Queue", dashboard.work_queue));
		$panels.append(renderListPanel("مهام معلقة", "Pending Tasks", dashboard.pending_tasks));
		$panels.append(renderListPanel("موافقات", "Approvals", dashboard.approvals));
		$dash.append($panels);

		const bd = dashboard.breakdowns || {};
		const $breakdowns = $('<div class="omnexa-portal-panels"></div>');
		$breakdowns.append(renderBreakdownTable("حسب الحالة", "By Status", bd.by_status, "status", "count"));
		$breakdowns.append(renderBreakdownTable("حسب العقار", "By Property", bd.by_property, "hotel_property", "count"));
		$breakdowns.append(renderBreakdownTable("حسب الطابق", "By Floor", bd.by_floor, "floor", "count"));
		$breakdowns.append(
			renderBreakdownTable("حسب المنطقة", "By Functional Area", bd.by_functional_area, "functional_area", "count")
		);
		$dash.append(`<h5 class="oj-section-title">${t("تحليلات", "Analytics")}</h5>`);
		$dash.append($breakdowns);

		if (dashboard.charts && dashboard.charts.length) {
			const $charts = $('<div class="omnexa-portal-charts"></div>');
			dashboard.charts.forEach((ch) => {
				const title = t(ch.title_ar, ch.title_en);
				$charts.append(
					`<div class="omnexa-portal-chart-placeholder">${frappe.utils.escape_html(title)} (${ch.type || "chart"})</div>`
				);
			});
			$dash.append(`<h5 class="oj-section-title">${t("مؤشرات بيانية", "Charts")}</h5>`);
			$dash.append($charts);
		}

		return $dash;
	}

	omnexa_fixed_assets.hotel_portal.mount = function (wrapper) {
		const currentRoute = `/app/${frappe.get_route_str().replace(/ /g, "-")}`;
		const page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Hotel Assets Dashboard"),
			single_column: true,
		});
		const $mount = $(page.body);
		$mount.html(`<div class="text-muted p-4">${__("Loading")}…</div>`);

		frappe.call({
			method: "omnexa_fixed_assets.api.get_hotel_assets_portal_context",
			callback(r) {
				const ctx = r.message || {};
				if (!ctx.ok) {
					$mount.html(
						`<div class="alert alert-warning">${frappe.utils.escape_html(ctx.message || __("Unable to load dashboard"))}</div>`
					);
					return;
				}

				const title = t(ctx.title_ar, ctx.title_en);
				const roleLabel = t(ctx.role_ar, ctx.role_en);

				const $layout = $('<div class="oj-vertical-portal-layout omnexa-multi-portal commerce"></div>');
				const $sidebar = $('<aside class="oj-vertical-portal-aside"></aside>');
				$sidebar.append(
					`<div class="oj-vertical-portal-brand">
						<strong>${frappe.utils.escape_html(title)}</strong>
					</div>`
				);
				$sidebar.append(renderSidebar(ctx.sidebar_portals || [], currentRoute));
				const $back = $(
					`<a class="oj-sidebar-link oj-sidebar-back" href="/app/fixed-assets">${t(
						"← مساحة الأصول",
						"← Fixed Assets"
					)}</a>`
				);
				$back.on("click", (e) => {
					e.preventDefault();
					frappe.set_route("fixed-assets");
				});
				$sidebar.append($back);

				const $main = $('<div class="oj-vertical-portal-main"></div>');
				$main.append(`<h3 class="oj-section-title">${frappe.utils.escape_html(title)}</h3>`);
				$main.append(
					`<p class="oj-muted">${t("النطاق", "Scope")}: <strong>${frappe.utils.escape_html(
						ctx.context_label || ctx.company || ""
					)}</strong> · ${t("بوابة", "Portal")}: <strong>${frappe.utils.escape_html(roleLabel)}</strong></p>`
				);

				if (ctx.dashboard) {
					$main.append(renderDashboard(ctx.dashboard));
				}

				$main.append(`<h5 class="oj-section-title">${t("القوائم التشغيلية", "Operational Menus")}</h5>`);
				$main.append(renderOperationalMenu(ctx.menu_sections || []));

				$layout.append($sidebar).append($main);
				$mount.empty().append($layout);

				if (wrapper && wrapper.page && wrapper.page.set_title) {
					wrapper.page.set_title(title);
				}
			},
		});
	};
})();
