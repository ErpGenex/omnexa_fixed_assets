frappe.pages["fa-asset-scan-pwa"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Asset Scan"),
		single_column: true,
	});

	const QUEUE_KEY = "omnexa_rfid_offline_queue";

	const $main = $(page.main);
	$main.addClass("omnexa-fa-scan-pwa").html(`
		<div class="omnexa-scan-card frappe-card" style="padding:16px;max-width:480px;margin:0 auto;">
			<h5>${__("Mobile Asset Operations")}</h5>
			<p class="text-muted">${__("Scan, locate, and inspect hotel assets from the field.")}</p>
			<div class="alert alert-secondary py-2 omnexa-offline-banner" style="display:none;"></div>
			<div class="form-group">
				<label>${__("Asset ID / RFID / QR")}</label>
				<input type="text" class="form-control omnexa-scan-input" placeholder="${__("Enter asset code")}" />
			</div>
			<div class="btn-group-vertical" style="width:100%;gap:8px;">
				<button class="btn btn-primary btn-block omnexa-btn-locate">${__("Locate Asset")}</button>
				<button class="btn btn-default btn-block omnexa-btn-scan">${__("Register RFID Scan")}</button>
				<button class="btn btn-default btn-block omnexa-btn-inspect">${__("Quick Inspection")}</button>
				<button class="btn btn-warning btn-block omnexa-btn-sync" style="display:none;">${__("Sync Offline Queue")}</button>
			</div>
			<div class="omnexa-scan-result" style="margin-top:16px;"></div>
		</div>
	`);

	function asset_code() {
		return ($main.find(".omnexa-scan-input").val() || "").trim();
	}

	function show_result(html) {
		$main.find(".omnexa-scan-result").html(html);
	}

	function load_queue() {
		try {
			return JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]");
		} catch (e) {
			return [];
		}
	}

	function save_queue(items) {
		localStorage.setItem(QUEUE_KEY, JSON.stringify(items || []));
		update_offline_ui();
	}

	function update_offline_ui() {
		const q = load_queue();
		const $banner = $main.find(".omnexa-offline-banner");
		const $sync = $main.find(".omnexa-btn-sync");
		if (q.length) {
			$banner.show().text(__("{0} scan(s) waiting to sync.", [q.length]));
			$sync.show();
		} else {
			$banner.hide();
			$sync.hide();
		}
	}

	function queue_offline_event(payload) {
		const q = load_queue();
		q.push({
			...payload,
			external_event_id: payload.external_event_id || frappe.utils.get_random(12),
			sequence_number: q.length + 1,
			queued_at: new Date().toISOString(),
		});
		save_queue(q);
		show_result(`<div class="alert alert-warning">${__("Offline — scan queued for sync.")}</div>`);
	}

	function resolve_asset(code) {
		return frappe.db.get_value("Fixed Asset", { name: code }, "name").then((r) => {
			if (r && r.message && r.message.name) return r.message.name;
			return frappe.db.get_value("Fixed Asset", { rfid_tag: code }, "name").then((r2) => {
				if (r2 && r2.message && r2.message.name) return r2.message.name;
				return frappe.db.get_value("Fixed Asset", { barcode: code }, "name").then(
					(r3) => (r3 && r3.message && r3.message.name) || code
				);
			});
		});
	}

	$main.on("click", ".omnexa-btn-locate", () => {
		const code = asset_code();
		if (!code) return frappe.msgprint(__("Enter an asset code."));
		resolve_asset(code).then((asset) => {
			frappe.call({
				method: "omnexa_fixed_assets.api.locate_asset",
				args: { asset },
				callback(r) {
					const msg = r.message || {};
					if (!msg.ok) return show_result(`<div class="text-danger">${__("Asset not found")}</div>`);
					const a = msg.asset || {};
					const scan = msg.last_scan || {};
					show_result(`<div class="alert alert-info">
						<strong>${frappe.utils.escape_html(a.asset_name || a.name)}</strong><br/>
						${__("Property")}: ${frappe.utils.escape_html(a.hotel_property || "—")}<br/>
						${__("Room")}: ${frappe.utils.escape_html(a.hotel_room || "—")}<br/>
						${__("Zone")}: ${frappe.utils.escape_html(a.hotel_zone || "—")}<br/>
						${__("Scan status")}: ${frappe.utils.escape_html(a.scan_status || "—")}<br/>
						${scan.scan_time ? `${__("Last scan")}: ${frappe.utils.escape_html(scan.location_text || "")} (${scan.scan_time})` : ""}
					</div>`);
				},
				error() {
					show_result(`<div class="text-danger">${__("Network error")}</div>`);
				},
			});
		});
	});

	$main.on("click", ".omnexa-btn-scan", () => {
		const code = asset_code();
		if (!code) return frappe.msgprint(__("Enter an asset code."));
		const payload = {
			rfid_tag: code,
			scan_result: "Seen",
			location_text: __("Mobile PWA scan"),
		};
		if (!navigator.onLine) {
			return queue_offline_event(payload);
		}
		frappe.call({
			method: "omnexa_fixed_assets.api.scan_asset",
			type: "POST",
			args: payload,
			callback(r) {
				const msg = r.message || {};
				if (msg.duplicate) {
					return show_result(`<div class="alert alert-secondary">${__("Duplicate scan suppressed.")}</div>`);
				}
				const label = msg.entity_type === "linen" ? msg.linen_item : msg.scan_log;
				show_result(`<div class="alert alert-success">${__("Scan logged")}: ${frappe.utils.escape_html(label || "")}</div>`);
			},
			error() {
				queue_offline_event(payload);
			},
		});
	});

	$main.on("click", ".omnexa-btn-inspect", () => {
		const code = asset_code();
		if (!code) return frappe.msgprint(__("Enter an asset code."));
		resolve_asset(code).then((asset) => {
			frappe.call({
				method: "omnexa_fixed_assets.api.submit_inspection",
				type: "POST",
				args: { asset, condition_status: "Good", notes: __("Mobile PWA inspection") },
				callback(r) {
					const msg = r.message || {};
					show_result(`<div class="alert alert-success">${__("Inspection created")}: ${frappe.utils.escape_html(msg.inspection || "")}</div>`);
				},
			});
		});
	});

	$main.on("click", ".omnexa-btn-sync", () => {
		const q = load_queue();
		if (!q.length) return update_offline_ui();
		frappe.call({
			method: "omnexa_fixed_assets.api.sync_offline_rfid_events",
			type: "POST",
			args: { events: q },
			callback(r) {
				const msg = r.message || {};
				save_queue([]);
				show_result(
					`<div class="alert alert-success">${__("Synced {0} event(s), {1} duplicate(s).", [
						msg.processed || 0,
						msg.duplicates || 0,
					])}</div>`
				);
			},
		});
	});

	window.addEventListener("online", () => {
		if (load_queue().length) {
			$main.find(".omnexa-btn-sync").trigger("click");
		}
	});

	update_offline_ui();
};
