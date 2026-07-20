// Copyright (c) 2026, Omnexa and contributors
// Expand Fixed Assets → Asset Insurance in the desk workspace sidebar.

(function () {
	const PARENT = "Fixed Assets";
	const CHILD_SLUGS = new Set(["fixed-assets", "asset-insurance"]);

	function current_slug() {
		const route = frappe.get_route() || [];
		return frappe.router.slug(route[0] || "");
	}

	function expand_fixed_assets_children() {
		if (!CHILD_SLUGS.has(current_slug())) {
			return;
		}
		const $parent = $(`.sidebar-item-container[item-name="${PARENT}"]`);
		if (!$parent.length) {
			return;
		}
		$parent.find(".sidebar-child-item").removeClass("hidden");
		const $use = $parent.find(".drop-icon use");
		if ($use.length) {
			$use.attr("href", "#es-line-up");
		}
	}

	function schedule_expand() {
		setTimeout(expand_fixed_assets_children, 80);
		setTimeout(expand_fixed_assets_children, 400);
	}

	frappe.router.on("change", schedule_expand);
	$(document).on("app_ready", schedule_expand);
	$(document).on("workspace_sidebar_reset", schedule_expand);
})();
