frappe.pages["fa-hospitality-command-center"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Hospitality Command Center"),
		single_column: true,
	});

	const $main = $(page.main);
	$main.html(`
		<div class="frappe-card" style="padding:16px;">
			<h5>${__("Hospitality Asset Command Center")}</h5>
			<div class="row omnexa-hcc-kpis" style="margin-top:12px;"></div>
			<hr/>
			<div class="row">
				<div class="col-md-7">
					<h6>${__("Live Movements")}</h6>
					<div class="omnexa-hcc-movements"></div>
				</div>
				<div class="col-md-5">
					<h6>${__("Active Alerts")}</h6>
					<div class="omnexa-hcc-alerts"></div>
				</div>
			</div>
		</div>
	`);

	function kpi(label, value, cls) {
		return `<div class="col-sm-4 col-md-3" style="margin-bottom:10px;">
			<div class="border rounded p-2 text-center ${cls || ""}">
				<div class="h5 mb-0">${value}</div>
				<div class="text-muted small">${label}</div>
			</div>
		</div>`;
	}

	function render(msg) {
		const h = (msg.hospitality || {});
		$main.find(".omnexa-hcc-kpis").html([
			kpi(__("Total Assets"), h.total_assets || 0),
			kpi(__("RFID Tagged"), h.tracked_assets || 0),
			kpi(__("RFID Online"), h.rfid_online || 0, "text-success"),
			kpi(__("RFID Offline"), h.rfid_offline || 0, "text-warning"),
			kpi(__("Moving Now"), h.assets_moving_now || 0),
			kpi(__("Missing Assets"), h.missing_assets || 0, "text-danger"),
			kpi(__("Missing Linen"), h.missing_linen || 0, "text-danger"),
			kpi(__("Unauthorized"), h.unauthorized_movements || 0, "text-danger"),
			kpi(__("Critical"), h.critical_assets_count || 0),
			kpi(__("Maintenance"), h.maintenance_assets || 0),
			kpi(__("AI Insights"), h.open_intelligence_recommendations || 0),
			kpi(__("Inspection %"), Math.round(msg.inspection_compliance_rate || 0) + "%"),
		].join(""));

		const $m = $main.find(".omnexa-hcc-movements").empty();
		frappe.call({
			method: "omnexa_fixed_assets.api.get_live_rfid_movements",
			args: { limit: 12 },
			callback(r) {
				(r.message?.movements || []).forEach((row) => {
					const label = row.entity_type === "linen"
						? `${row.linen_item} → ${row.location || ""}`
						: `${row.asset || ""} ${row.remarks || ""}`;
					$m.append(`<div class="small text-muted">${frappe.utils.escape_html(row.timestamp || "")} — ${frappe.utils.escape_html(label)}</div>`);
				});
				if (!$m.children().length) $m.html(`<div class="text-muted small">${__("No recent movements.")}</div>`);
			},
		});

		const $a = $main.find(".omnexa-hcc-alerts").empty();
		(msg.active_alerts || []).slice(0, 8).forEach((row) => {
			$a.append(`<div class="alert alert-warning py-1 px-2 small">${frappe.utils.escape_html(row.message || row.alert_type || row.name)}</div>`);
		});
		if (!(msg.active_alerts || []).length) $a.html(`<div class="text-muted small">${__("No open alerts.")}</div>`);
	}

	function refresh() {
		frappe.call({
			method: "omnexa_fixed_assets.api.get_asset_command_center",
			callback(r) {
				if (r.message?.ok) render(r.message);
			},
		});
	}

	frappe.realtime.on("omnexa_rfid_movement", refresh);
	frappe.realtime.on("omnexa_linen_movement", refresh);
	refresh();
	setInterval(refresh, 45000);
};
