frappe.pages["fa-global-hospitality-portfolio"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Global Hospitality Portfolio"),
		single_column: true,
	});

	const $main = $(page.main);
	$main.html(`
		<div class="frappe-card" style="padding:16px;">
			<h5>${__("Enterprise Portfolio Rollup")}</h5>
			<div class="row omnexa-portfolio-kpis" style="margin-top:12px;"></div>
			<hr/>
			<h6>${__("Properties")}</h6>
			<div class="table-responsive"><table class="table table-bordered table-sm omnexa-portfolio-table">
				<thead><tr>
					<th>${__("Property")}</th><th>${__("Branch")}</th><th>${__("Assets")}</th>
					<th>${__("RFID")}</th><th>${__("Missing")}</th><th>${__("Linen")}</th><th>${__("Health")}</th>
				</tr></thead><tbody></tbody>
			</table></div>
			<hr/>
			<h6>${__("Predictive Analytics")}</h6>
			<div class="omnexa-predictive"></div>
		</div>
	`);

	function renderPortfolio(msg) {
		const r = msg.rollup || {};
		$main.find(".omnexa-portfolio-kpis").html([
			["Properties", r.total_properties],
			["Branches", r.total_branches],
			["Assets", r.total_assets],
			["RFID Tagged", r.rfid_tagged],
			["Missing Assets", r.missing_assets],
			["Missing Linen", r.missing_linen],
			["RFID Online", r.rfid_online],
			["Open Alerts", r.open_alerts],
		].map(([label, val]) => `<div class="col-sm-3" style="margin-bottom:8px;"><div class="border rounded p-2 text-center"><div class="h5">${val || 0}</div><div class="text-muted small">${label}</div></div></div>`).join(""));

		const $tb = $main.find(".omnexa-portfolio-table tbody").empty();
		(msg.properties || []).forEach((p) => {
			$tb.append(`<tr>
				<td>${frappe.utils.escape_html(p.property_name || p.property)}</td>
				<td>${frappe.utils.escape_html(p.branch || "")}</td>
				<td>${p.assets || 0}</td>
				<td>${p.rfid_tagged || 0}</td>
				<td>${p.missing_assets || 0}</td>
				<td>${p.linen || 0}</td>
				<td>${p.health_avg || 0}</td>
			</tr>`);
		});
	}

	frappe.call({
		method: "omnexa_fixed_assets.api.get_global_hospitality_portfolio",
		callback(r) {
			if (r.message?.ok) renderPortfolio(r.message);
		},
	});

	frappe.call({
		method: "omnexa_fixed_assets.api.get_predictive_analytics",
		callback(r) {
			const a = r.message?.analytics || {};
			const $p = $main.find(".omnexa-predictive").empty();
			const loss = a.linen_loss_rate || {};
			$p.append(`<div class="small">${__("Linen loss rate")}: ${loss.rate_pct || 0}% · ${__("7d RFID moves")}: ${(a.movement_velocity || {}).rfid_movements_7d || 0}</div>`);
			(a.missing_asset_risk || []).slice(0, 5).forEach((row) => {
				$p.append(`<div class="alert alert-warning py-1 small">${frappe.utils.escape_html(row.asset)} — ${__("risk")} ${row.risk_score}%</div>`);
			});
		},
	});
};
