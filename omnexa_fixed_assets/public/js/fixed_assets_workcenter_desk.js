/* global frappe */
frappe.provide("omnexa_fixed_assets.workcenter");

(function () {
	"use strict";

	function t(ar, en) {
		return frappe.boot.lang === "ar" ? ar : en;
	}

	function navigateRoute(route) {
		if (!route) return;
		if (route === "/app/fixed-assets") {
			frappe.set_route("fixed-assets");
			return;
		}
		if (route.startsWith("/app/")) {
			const slug = route.replace(/^\/app\//, "").replace(/\/$/, "");
			if (slug) {
				frappe.set_route(slug);
				return;
			}
		}
		window.location.href = route;
	}

	function renderSidebar(links, activeRoute) {
		const $nav = $('<nav class="oj-vertical-portal-sidebar"></nav>');
		(links || []).forEach((item) => {
			const label = t(item.label_ar, item.label_en);
			const active = item.route === activeRoute ? " active" : "";
			const $link = $(`
				<a class="oj-sidebar-link${active}" href="${frappe.utils.escape_html(item.route)}">
					<span class="oj-sidebar-icon">${item.icon || "📁"}</span>
					<span>${frappe.utils.escape_html(label)}</span>
				</a>`);
			$link.on("click", (e) => {
				e.preventDefault();
				navigateRoute(item.route);
			});
			$nav.append($link);
		});
		return $nav;
	}

	function renderPortalGroups(groups) {
		const $root = $('<div class="omnexa-fa-workcenter-portals"></div>');
		(groups || []).forEach((group) => {
			const title = t(group.label_ar, group.label_en);
			const $sec = $(`<div class="oj-portal-section"><h4 class="oj-portal-cat-title">${frappe.utils.escape_html(title)}</h4></div>`);
			const $grid = $('<div class="oj-clinic-grid omnexa-fa-portal-grid"></div>');
			(group.portals || []).forEach((portal) => {
				const name = t(portal.label_ar, portal.label_en);
				const subtitle = t(portal.subtitle_ar, portal.subtitle_en);
				const $card = $(`
					<div class="oj-clinic-card omnexa-fa-portal-card">
						<div class="oj-clinic-icon">${portal.icon || "📁"}</div>
						<h4>${frappe.utils.escape_html(name)}</h4>
						<p class="oj-muted">${frappe.utils.escape_html(subtitle)}</p>
					</div>`);
				$card.on("click", () => navigateRoute(portal.route));
				$grid.append($card);
			});
			$sec.append($grid);
			$root.append($sec);
		});
		return $root;
	}

	function renderKpis(kpis) {
		if (!kpis || !kpis.length) return $();
		const $row = $('<div class="row omnexa-fa-wc-kpis" style="margin-bottom:16px;"></div>');
		kpis.forEach((kpi) => {
			const label = t(kpi.label_ar, kpi.label_en);
			$row.append(`
				<div class="col-sm-6 col-md-3" style="margin-bottom:10px;">
					<div class="border rounded p-3 text-center">
						<div class="h4 mb-0">${frappe.utils.escape_html(String(kpi.value ?? "—"))}</div>
						<div class="text-muted small">${frappe.utils.escape_html(label)}</div>
					</div>
				</div>`);
		});
		return $row;
	}

	omnexa_fixed_assets.workcenter.mount = function (wrapper) {
		const page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Fixed Assets Workcenter"),
			single_column: true,
		});
		const $main = $(page.main);
		$main.html(`<div class="frappe-card" style="padding:16px;"><div class="text-muted">${__("Loading…")}</div></div>`);

		frappe.call({
			method: "omnexa_fixed_assets.fixed_assets_portal_catalog.get_workcenter_context",
			callback(r) {
				const ctx = r.message || {};
				const activeRoute = "/app/fixed-assets-workcenter";
				const $card = $('<div class="frappe-card" style="padding:16px;"></div>');
				const $layout = $('<div class="oj-vertical-portal-layout"></div>');
				const $aside = $('<aside class="oj-vertical-portal-aside"></aside>');
				$aside.append(`
					<div class="oj-vertical-portal-brand">
						${ctx.logo_url ? `<img src="${frappe.utils.escape_html(ctx.logo_url)}" alt="" />` : ""}
						<strong>${frappe.utils.escape_html(t(ctx.title_ar, ctx.title_en))}</strong>
					</div>`);
				$aside.append(renderSidebar(ctx.sidebar || [], activeRoute));

				const $body = $('<div class="oj-vertical-portal-main"></div>');
				$body.append(`<h4>${frappe.utils.escape_html(t("مركز عمل الأصول الثابتة", "Fixed Assets Workcenter"))}</h4>`);
				$body.append(`<p class="text-muted">${frappe.utils.escape_html(
					t("إدارة الأصول · الضيافة · RFID · بدون خلط مع أنشطة أخرى", "Asset management · hospitality · RFID · no cross-activity bleed")
				)}</p>`);
				if (ctx.company) {
					$body.append(
						`<p class="text-muted small">${frappe.utils.escape_html(ctx.company)}${ctx.branch ? " · " + frappe.utils.escape_html(ctx.branch) : ""}</p>`
					);
				}
				$body.append(renderKpis(ctx.kpis));
				$body.append(renderPortalGroups(ctx.grouped_portals || []));

				$layout.append($aside).append($body);
				$card.append($layout);
				$main.empty().append($card);
			},
		});
	};
})();
