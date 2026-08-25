frappe.pages["fa-live-asset-tracking"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Live Asset Tracking"),
		single_column: true,
	});

	const $main = $(page.main);
	$main.addClass("omnexa-live-map").html(`
		<div class="frappe-card" style="padding:16px;">
			<div class="row">
				<div class="col-sm-6">
					<h5>${__("Hotel Floor Map (Live)")}</h5>
					<p class="text-muted">${__("Heatmap + optional SVG floor plan.")}</p>
				</div>
				<div class="col-sm-3">
					<select class="form-control omnexa-floor-filter"><option value="">${__("All Floors")}</option></select>
				</div>
				<div class="col-sm-3 text-right">
					<span class="badge omnexa-live-status">${__("Connecting…")}</span>
				</div>
			</div>
			<div class="omnexa-svg-plan" style="display:none;margin-top:12px;overflow:auto;max-height:420px;"></div>
			<div class="omnexa-live-grid row" style="margin-top:12px;"></div>
			<hr/>
			<h6>${__("Recent Movements")}</h6>
			<div class="omnexa-live-feed"></div>
		</div>
	`);

	let pollTimer = null;
	let heatmapCells = {};
	let selectedFloor = "";

	function heatColor(cell) {
		const score = (cell.movement_density || 0) * 2 + (cell.loss_density || 0) * 5 + (cell.asset_density || 0);
		if (score >= 15) return "#fde2e2";
		if (score >= 8) return "#fff3cd";
		if (score >= 3) return "#e8f4fd";
		return "#f8f9fa";
	}

	function render(payload) {
		const rooms = payload.rooms || [];
		const assets = payload.assets || [];
		const byRoom = {};
		assets.forEach((a) => {
			const key = a.hotel_room || __("Unassigned");
			(byRoom[key] = byRoom[key] || []).push(a);
		});
		const $grid = $main.find(".omnexa-live-grid").empty();
		const filteredRooms = selectedFloor
			? rooms.filter((r) => (r.floor || "") === selectedFloor)
			: rooms;
		filteredRooms.slice(0, 36).forEach((room) => {
			const list = byRoom[room.name] || [];
			const cell = heatmapCells[room.name] || {};
			const bg = heatColor(cell);
			const chips = list
				.slice(0, 6)
				.map(
					(a) =>
						`<span class="badge badge-info" title="${frappe.utils.escape_html(a.asset_name || a.name)}">${frappe.utils.escape_html(a.name)}</span>`
				)
				.join(" ");
			$grid.append(`
				<div class="col-sm-4 col-md-3" style="margin-bottom:12px;">
					<div class="border rounded" style="padding:10px;min-height:90px;background:${bg};">
						<strong>${frappe.utils.escape_html(room.room_number || room.name)}</strong>
						<div class="text-muted small">${frappe.utils.escape_html(room.floor || "")} ${frappe.utils.escape_html(room.wing || "")}</div>
						<div class="text-muted small">${__("Assets")}: ${cell.asset_density || list.length} · ${__("Moves")}: ${cell.movement_density || 0}</div>
						<div style="margin-top:6px;">${chips || `<span class="text-muted small">${__("No assets")}</span>`}</div>
					</div>
				</div>
			`);
		});
		const $feed = $main.find(".omnexa-live-feed").empty();
		(payload.movements || []).slice(0, 15).forEach((m) => {
			const label =
				m.entity_type === "linen"
					? `${m.linen_item} → ${m.location || ""}`
					: `${m.asset || ""} ${m.remarks || ""}`;
			$feed.append(`<div class="small text-muted">${frappe.utils.escape_html(m.timestamp || "")} — ${frappe.utils.escape_html(label)}</div>`);
		});
		$main.find(".omnexa-live-status").text(__("Live")).removeClass("badge-secondary").addClass("badge-success");
	}

	function refresh() {
		frappe.call({
			method: "omnexa_fixed_assets.api.get_live_asset_map",
			callback(r) {
				if (r.message && r.message.ok) render(r.message);
			},
		});
		frappe.call({
			method: "omnexa_fixed_assets.api.get_asset_heatmap",
			args: { floor: selectedFloor || undefined },
			callback(r) {
				const msg = r.message || {};
				heatmapCells = {};
				(msg.cells || []).forEach((c) => {
					heatmapCells[c.room] = c;
				});
				const $sel = $main.find(".omnexa-floor-filter");
				if ($sel.children().length <= 1 && (msg.floors || []).length) {
					msg.floors.forEach((f) => $sel.append(`<option value="${frappe.utils.escape_html(f)}">${frappe.utils.escape_html(f)}</option>`));
				}
			},
		});
		if (selectedFloor) {
			frappe.call({
				method: "omnexa_fixed_assets.api.get_floor_plan",
				args: { floor: selectedFloor },
				callback(r) {
					const plan = r.message?.plan;
					const $svg = $main.find(".omnexa-svg-plan");
					if (plan && plan.svg_content) {
						$svg.show().html(plan.svg_content);
					} else if (plan && plan.attach_image) {
						$svg.show().html(`<img src="${plan.attach_image}" style="max-width:100%;"/>`);
					} else {
						$svg.hide().empty();
					}
				},
			});
		} else {
			$main.find(".omnexa-svg-plan").hide().empty();
		}
	}

	$main.on("change", ".omnexa-floor-filter", function () {
		selectedFloor = $(this).val() || "";
		refresh();
	});

	frappe.realtime.on("omnexa_rfid_movement", () => refresh());
	frappe.realtime.on("omnexa_linen_movement", () => refresh());
	refresh();
	pollTimer = setInterval(refresh, 30000);
	$(wrapper).on("remove", () => pollTimer && clearInterval(pollTimer));
};
