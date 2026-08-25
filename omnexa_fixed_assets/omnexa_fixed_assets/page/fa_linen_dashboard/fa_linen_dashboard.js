frappe.pages["fa-linen-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Linen Dashboard"),
		single_column: true,
	});

	const $main = $(page.main);
	$main.html(`
		<div class="frappe-card" style="padding:16px;">
			<div class="row omnexa-linen-kpis"></div>
			<hr/>
			<h6>${__("Open Shortages")}</h6>
			<div class="omnexa-linen-shortages"></div>
			<hr/>
			<h6>${__("Replacement Warnings")}</h6>
			<div class="omnexa-linen-replacement"></div>
		</div>
	`);

	function render(msg) {
		const k = msg.kpis || {};
		$main.find(".omnexa-linen-kpis").html(`
			<div class="col-sm-3"><div class="border rounded p-3 text-center"><div class="h4">${k.total_linen || 0}</div><div class="text-muted">${__("Total Linen")}</div></div></div>
			<div class="col-sm-3"><div class="border rounded p-3 text-center"><div class="h4 text-danger">${k.missing_linen || 0}</div><div class="text-muted">${__("Missing")}</div></div></div>
			<div class="col-sm-3"><div class="border rounded p-3 text-center"><div class="h4 text-warning">${k.open_shortages || 0}</div><div class="text-muted">${__("Shortages")}</div></div></div>
			<div class="col-sm-3"><div class="border rounded p-3 text-center"><div class="h4">${k.replacement_warnings || 0}</div><div class="text-muted">${__("Replace Soon")}</div></div></div>
		`);
		const $s = $main.find(".omnexa-linen-shortages").empty();
		(msg.shortages || []).forEach((row) => {
			$s.append(`<div class="alert alert-warning py-2">${frappe.utils.escape_html(row.message || row.name)}</div>`);
		});
		if (!(msg.shortages || []).length) $s.html(`<div class="text-muted small">${__("No open shortages.")}</div>`);
		const $r = $main.find(".omnexa-linen-replacement").empty();
		(msg.replacement_warnings || []).forEach((row) => {
			const rem = int(row.expected_life_cycles) - int(row.wash_count);
			$r.append(`<div class="small">${frappe.utils.escape_html(row.name)} — ${frappe.utils.escape_html(row.linen_type)} (${rem} ${__("cycles left")})</div>`);
		});
		if (!(msg.replacement_warnings || []).length) $r.html(`<div class="text-muted small">${__("No replacement warnings.")}</div>`);
	}

	function int(v) {
		return parseInt(v || 0, 10);
	}

	frappe.call({
		method: "omnexa_fixed_assets.api.get_linen_dashboard",
		callback(r) {
			if (r.message && r.message.ok) render(r.message);
		},
	});
};
