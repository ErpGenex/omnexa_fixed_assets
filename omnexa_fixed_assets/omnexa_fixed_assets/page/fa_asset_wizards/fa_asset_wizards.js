frappe.pages["fa-asset-wizards"].on_page_load = function (wrapper) {
	frappe.require("/assets/omnexa_fixed_assets/css/asset_wizards.css");

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Asset Lifecycle Wizards"),
		single_column: true,
	});

	const state = { session: null, stepIndex: 0, catalog: [] };
	const $main = $(page.main);

	function shell() {
		$main.html(`
			<div class="frappe-card omnexa-wiz-shell" style="padding:16px;">
				<div class="omnexa-wiz-home"></div>
				<div class="omnexa-wiz-runner" style="display:none;"></div>
			</div>
		`);
	}

	function renderHome() {
		state.session = null;
		state.stepIndex = 0;
		$main.find(".omnexa-wiz-home").show();
		$main.find(".omnexa-wiz-runner").hide().empty();

		const $home = $main.find(".omnexa-wiz-home");
		$home.html(`
			<h5>${__("Asset Lifecycle Wizards")}</h5>
			<p class="text-muted">${__("Multi-step guided workflows over existing Fixed Asset, transfer, maintenance, finance, and RFID records.")}</p>
			<h6 class="mt-3">${__("Start a Wizard")}</h6>
			<div class="row omnexa-wiz-catalog"></div>
			<hr/>
			<h6>${__("My Drafts")}</h6>
			<div class="omnexa-wiz-drafts text-muted small">${__("Loading…")}</div>
		`);

		frappe.call({
			method: "omnexa_fixed_assets.api.get_wizard_catalog",
			callback(r) {
				state.catalog = r.message?.wizards || [];
				const $cat = $home.find(".omnexa-wiz-catalog").empty();
				state.catalog.forEach((w) => {
					$cat.append(`
						<div class="col-md-4 col-lg-3" style="margin-bottom:12px;">
							<div class="border rounded p-3 wiz-card" data-type="${frappe.utils.escape_html(w.wizard_type)}">
								<div class="font-weight-bold">${frappe.utils.escape_html(__(w.title))}</div>
								<div class="text-muted small mt-1">${frappe.utils.escape_html(__(w.description || ""))}</div>
								<div class="text-muted small mt-2">${w.step_count || 0} ${__("steps")}</div>
							</div>
						</div>
					`);
				});
				$cat.find(".wiz-card").on("click", function () {
					startWizard($(this).data("type"));
				});
			},
		});

		frappe.call({
			method: "omnexa_fixed_assets.api.list_wizard_drafts",
			callback(r) {
				const drafts = r.message?.drafts || [];
				const $d = $home.find(".omnexa-wiz-drafts").empty();
				if (!drafts.length) {
					$d.html(`<div class="text-muted">${__("No drafts.")}</div>`);
					return;
				}
				drafts.forEach((row) => {
					$d.append(`
						<div class="d-flex justify-content-between align-items-center border-bottom py-2">
							<div>
								<strong>${frappe.utils.escape_html(row.wizard_type)}</strong>
								<span class="text-muted"> — ${frappe.utils.escape_html(row.name)} (${frappe.utils.escape_html(row.status)})</span>
							</div>
							<button class="btn btn-xs btn-default resume-draft" data-name="${frappe.utils.escape_html(row.name)}">${__("Resume")}</button>
						</div>
					`);
				});
				$d.find(".resume-draft").on("click", function () {
					loadSession($(this).data("name"));
				});
			},
		});
	}

	function startWizard(wizardType) {
		frappe.call({
			method: "omnexa_fixed_assets.api.start_wizard",
			args: { wizard_type: wizardType },
			freeze: true,
			callback(r) {
				if (r.message?.session) {
					openRunner(r.message.session);
				}
			},
		});
	}

	function loadSession(name) {
		frappe.call({
			method: "omnexa_fixed_assets.api.get_wizard_session",
			args: { session_name: name },
			callback(r) {
				if (r.message?.session) openRunner(r.message.session);
			},
		});
	}

	function openRunner(session) {
		state.session = session;
		state.stepIndex = session.current_step || 0;
		$main.find(".omnexa-wiz-home").hide();
		const $run = $main.find(".omnexa-wiz-runner").show();
		renderRunner($run);
	}

	function renderRunner($run) {
		const s = state.session;
		const steps = s.steps || [];
		const current = steps[state.stepIndex] || {};
		const isReview = current.key === "review";

		let progress = `<div class="d-flex flex-wrap omnexa-wiz-progress mb-3">`;
		steps.forEach((st, idx) => {
			let cls = "step-dot mr-2 mb-2";
			if (idx < state.stepIndex) cls += " done";
			else if (idx === state.stepIndex) cls += " active";
			progress += `<div class="${cls}" title="${frappe.utils.escape_html(st.label)}">${idx + 1}</div>`;
		});
		progress += `</div>`;

		$run.html(`
			<div class="d-flex justify-content-between align-items-start mb-2">
				<div>
					<h5 class="mb-0">${frappe.utils.escape_html(s.title || s.wizard_type)}</h5>
					<div class="text-muted small">${frappe.utils.escape_html(s.name)} · ${frappe.utils.escape_html(s.status)}</div>
				</div>
				<button class="btn btn-sm btn-default back-home">${__("Back to Catalog")}</button>
			</div>
			${progress}
			<h6>${frappe.utils.escape_html(current.label || __("Step"))}</h6>
			<div class="omnexa-wiz-step-body"></div>
			<div class="mt-3 d-flex justify-content-between">
				<button class="btn btn-default btn-sm prev-step" ${state.stepIndex === 0 ? "disabled" : ""}>${__("Previous")}</button>
				<div>
					<button class="btn btn-default btn-sm cancel-wiz">${__("Cancel")}</button>
					<button class="btn btn-primary btn-sm next-step">${isReview ? __("Submit") : __("Save & Continue")}</button>
				</div>
			</div>
		`);

		$run.find(".back-home").on("click", renderHome);
		$run.find(".prev-step").on("click", () => {
			if (state.stepIndex > 0) {
				state.stepIndex -= 1;
				renderRunner($run);
			}
		});
		$run.find(".cancel-wiz").on("click", () => {
			frappe.confirm(__("Cancel this wizard session?"), () => {
				frappe.call({
					method: "omnexa_fixed_assets.api.cancel_wizard",
					args: { session_name: s.name },
					callback() {
						frappe.show_alert({ message: __("Wizard cancelled"), indicator: "orange" });
						renderHome();
					},
				});
			});
		});
		$run.find(".next-step").on("click", () => saveAndAdvance($run, isReview));

		if (isReview) renderReview($run.find(".omnexa-wiz-step-body"));
		else renderStepForm($run.find(".omnexa-wiz-step-body"), current);
	}

	function stepValues(stepKey) {
		return (state.session.step_data || {})[stepKey] || {};
	}

	function renderStepForm($body, step) {
		const key = step.key;
		const vals = stepValues(key);
		const fields = STEP_FIELDS[key] || STEP_FIELDS._default;
		let html = `<div class="omnexa-wiz-step-form row">`;
		fields.forEach((f) => {
			const v = vals[f.fieldname] != null ? vals[f.fieldname] : (f.default || "");
			html += `<div class="form-group col-md-6" data-field="${f.fieldname}">
				<label>${__(f.label)}${f.reqd ? " *" : ""}</label>`;
			if (f.fieldtype === "Select") {
				html += `<select class="form-control input-${f.fieldname}">`;
				(f.options || []).forEach((opt) => {
					html += `<option value="${frappe.utils.escape_html(opt)}" ${String(v) === String(opt) ? "selected" : ""}>${frappe.utils.escape_html(opt)}</option>`;
				});
				html += `</select>`;
			} else if (f.fieldtype === "Check") {
				html += `<input type="checkbox" class="input-${f.fieldname}" ${v ? "checked" : ""}/>`;
			} else if (f.fieldtype === "Link") {
				html += `<input type="text" class="form-control input-${f.fieldname}" data-doctype="${f.options}" value="${frappe.utils.escape_html(String(v))}"/>`;
			} else if (f.fieldtype === "Date") {
				html += `<input type="date" class="form-control input-${f.fieldname}" value="${frappe.utils.escape_html(String(v))}"/>`;
			} else if (f.fieldtype === "Float" || f.fieldtype === "Currency") {
				html += `<input type="number" step="0.01" class="form-control input-${f.fieldname}" value="${frappe.utils.escape_html(String(v))}"/>`;
			} else if (f.fieldtype === "Text") {
				html += `<textarea class="form-control input-${f.fieldname}" rows="3">${frappe.utils.escape_html(String(v))}</textarea>`;
			} else {
				html += `<input type="text" class="form-control input-${f.fieldname}" value="${frappe.utils.escape_html(String(v))}"/>`;
			}
			html += `</div>`;
		});
		html += `</div>`;

		if (key === "select_asset") {
			html += `
				<div class="mt-2">
					<button type="button" class="btn btn-xs btn-default resolve-asset">${__("Lookup by RFID / Barcode")}</button>
					<div class="omnexa-wiz-asset-preview small text-muted mt-2"></div>
				</div>`;
		}
		if (key === "preview" && state.session.wizard_type === "depreciation") {
			html += `<div class="omnexa-wiz-dep-preview alert alert-info mt-2">${__("Loading preview…")}</div>`;
		}

		$body.html(html);

		if (key === "select_asset") {
			$body.find(".resolve-asset").on("click", () => {
				frappe.prompt(
					[{ fieldname: "identifier", label: __("Asset ID / RFID / Barcode"), fieldtype: "Data", reqd: 1 }],
					(values) => {
						frappe.call({
							method: "omnexa_fixed_assets.api.resolve_asset_for_wizard",
							args: { identifier: values.identifier },
							callback(r) {
								const asset = r.message?.asset;
								if (!asset) {
									frappe.msgprint(__("Asset not found."));
									return;
								}
								$body.find(".input-fixed_asset").val(asset.name);
								$body.find(".omnexa-wiz-asset-preview").html(
									`<strong>${frappe.utils.escape_html(asset.asset_name || asset.name)}</strong> — ${frappe.utils.escape_html(asset.status || "")} · ${frappe.utils.escape_html(asset.hotel_room || "")}`
								);
							},
						});
					},
					__("Resolve Asset")
				);
			});
		}

		if (key === "preview" && state.session.wizard_type === "depreciation") {
			const asset = stepValues("select_asset").fixed_asset;
			const pd = stepValues("posting").posting_date || frappe.datetime.get_today();
			if (asset) {
				frappe.call({
					method: "omnexa_fixed_assets.api.preview_wizard_depreciation",
					args: { asset, posting_date: pd },
					callback(r) {
						const amt = r.message?.depreciation_amount;
						$body.find(".omnexa-wiz-dep-preview").html(
							`${__("Suggested depreciation")}: <strong>${format_currency(amt)}</strong> (${frappe.utils.escape_html(String(r.message?.posting_date || pd))})`
						);
					},
				});
			}
		}
	}

	function renderReview($body) {
		$body.html(`
			<div class="omnexa-wiz-review">
				<p class="text-muted">${__("Review collected data before final submission. This will create or update the underlying ERP records atomically.")}</p>
				<pre>${frappe.utils.escape_html(JSON.stringify(state.session.step_data || {}, null, 2))}</pre>
			</div>
		`);
	}

	function collectPayload(stepKey) {
		const fields = STEP_FIELDS[stepKey] || STEP_FIELDS._default;
		const payload = {};
		const $form = $main.find(".omnexa-wiz-step-form");
		fields.forEach((f) => {
			const $el = $form.find(`.input-${f.fieldname}`);
			if (!$el.length) return;
			if (f.fieldtype === "Check") payload[f.fieldname] = $el.is(":checked") ? 1 : 0;
			else payload[f.fieldname] = $el.val();
		});
		return payload;
	}

	function saveAndAdvance($run, isReview) {
		const s = state.session;
		const steps = s.steps || [];
		const current = steps[state.stepIndex] || {};

		if (isReview) {
			frappe.call({
				method: "omnexa_fixed_assets.api.submit_wizard",
				args: { session_name: s.name },
				freeze: true,
				callback(r) {
					if (r.message?.ok) {
						const res = r.message.result || {};
						frappe.show_alert({ message: __("Wizard completed"), indicator: "green" });
						if (res.result_doctype && res.result_name) {
							frappe.msgprint(
								`${__("Created")}: <a href="/app/${frappe.router.slug(res.result_doctype)}/${res.result_name}">${res.result_name}</a>`
							);
						}
						state.session = r.message.session;
						renderHome();
					}
				},
			});
			return;
		}

		const payload = collectPayload(current.key);
		frappe.call({
			method: "omnexa_fixed_assets.api.save_wizard_step",
			args: { session_name: s.name, step_key: current.key, payload: JSON.stringify(payload) },
			freeze: true,
			callback(r) {
				if (!r.message?.ok) {
					frappe.msgprint((r.message?.errors || [__("Validation failed.")]).join("<br>"));
					return;
				}
				state.session = r.message.session;
				if (state.stepIndex < steps.length - 1) {
					state.stepIndex += 1;
					renderRunner($run);
				}
			},
		});
	}

	function format_currency(val) {
		try {
			return frappe.format(val, { fieldtype: "Currency" });
		} catch (e) {
			return String(val ?? "");
		}
	}

	const STEP_FIELDS = {
		_default: [],
		classification: [{ fieldname: "category", label: __("Category"), fieldtype: "Link", options: "Fixed Asset Category", reqd: 1 }],
		basic_info: [
			{ fieldname: "asset_name", label: __("Asset Name"), fieldtype: "Data", reqd: 1 },
			{ fieldname: "notes", label: __("Notes"), fieldtype: "Text" },
		],
		location: [
			{ fieldname: "hotel_property", label: __("Hotel Property"), fieldtype: "Link", options: "Hotel Property" },
			{ fieldname: "hotel_room", label: __("Hotel Room"), fieldtype: "Link", options: "Hotel Room" },
			{ fieldname: "hotel_zone", label: __("Hotel Zone"), fieldtype: "Data" },
			{ fieldname: "exact_position", label: __("Exact Position"), fieldtype: "Data" },
		],
		financial: [
			{ fieldname: "acquisition_cost", label: __("Acquisition Cost"), fieldtype: "Currency" },
			{ fieldname: "salvage_value", label: __("Salvage Value"), fieldtype: "Currency" },
			{ fieldname: "capitalization_date", label: __("Capitalization Date"), fieldtype: "Date" },
		],
		depreciation: [
			{ fieldname: "depreciation_method", label: __("Method"), fieldtype: "Select", options: ["Straight Line", "Declining Balance"], default: "Straight Line" },
			{ fieldname: "useful_life_months", label: __("Useful Life (months)"), fieldtype: "Float", default: 60 },
			{ fieldname: "depreciation_start_date", label: __("Start Date"), fieldtype: "Date" },
		],
		tracking: [
			{ fieldname: "rfid_tag", label: __("RFID Tag"), fieldtype: "Data" },
			{ fieldname: "barcode", label: __("Barcode"), fieldtype: "Data" },
		],
		inspection: [
			{ fieldname: "condition_status", label: __("Condition"), fieldtype: "Select", options: ["Excellent", "Good", "Fair", "Poor", "Critical"] },
			{ fieldname: "notes", label: __("Notes"), fieldtype: "Text" },
		],
		select_asset: [{ fieldname: "fixed_asset", label: __("Fixed Asset"), fieldtype: "Link", options: "Fixed Asset", reqd: 1 }],
		current_location: [],
		destination: [
			{ fieldname: "to_hotel_property", label: __("To Property"), fieldtype: "Link", options: "Hotel Property" },
			{ fieldname: "to_hotel_room", label: __("To Room"), fieldtype: "Link", options: "Hotel Room", reqd: 1 },
		],
		reason: [
			{ fieldname: "transfer_reason", label: __("Transfer Reason"), fieldtype: "Text", reqd: 1 },
			{ fieldname: "posting_date", label: __("Posting Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		],
		work_order: [
			{ fieldname: "description", label: __("Description"), fieldtype: "Text", reqd: 1 },
			{ fieldname: "work_order_type", label: __("Type"), fieldtype: "Select", options: ["Corrective", "Preventive", "Inspection-Triggered"] },
			{ fieldname: "priority", label: __("Priority"), fieldtype: "Select", options: ["Low", "Medium", "High", "Critical"] },
			{ fieldname: "assigned_to", label: __("Assigned To"), fieldtype: "Link", options: "User" },
		],
		authorization: [{ fieldname: "authorized_by", label: __("Authorized By"), fieldtype: "Link", options: "User" }],
		work_order_close: [{ fieldname: "work_order", label: __("Work Order"), fieldtype: "Link", options: "Asset Work Order", reqd: 1 }],
		condition: [
			{ fieldname: "condition_status", label: __("Condition"), fieldtype: "Select", options: ["Excellent", "Good", "Fair", "Poor", "Critical"], reqd: 1 },
			{ fieldname: "notes", label: __("Notes"), fieldtype: "Text" },
		],
		disposal_details: [
			{ fieldname: "disposal_date", label: __("Disposal Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
			{ fieldname: "proceeds", label: __("Proceeds"), fieldtype: "Currency" },
			{ fieldname: "remarks", label: __("Remarks"), fieldtype: "Text" },
		],
		accounts: [
			{ fieldname: "cash_account", label: __("Cash Account"), fieldtype: "Link", options: "Account", reqd: 1 },
			{ fieldname: "gain_or_loss_account", label: __("Gain/Loss Account"), fieldtype: "Link", options: "Account", reqd: 1 },
		],
		posting: [{ fieldname: "posting_date", label: __("Posting Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() }],
		preview: [],
		assessment: [
			{ fieldname: "revalued_amount", label: __("Revalued Amount"), fieldtype: "Currency" },
			{ fieldname: "posting_date", label: __("Posting Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
			{ fieldname: "condition_status", label: __("Condition (alternative)"), fieldtype: "Select", options: ["", "Excellent", "Good", "Fair", "Poor", "Critical"] },
			{ fieldname: "remarks", label: __("Remarks"), fieldtype: "Text" },
		],
		correct_location: [
			{ fieldname: "hotel_property", label: __("Hotel Property"), fieldtype: "Link", options: "Hotel Property", reqd: 1 },
			{ fieldname: "hotel_room", label: __("Hotel Room"), fieldtype: "Link", options: "Hotel Room" },
			{ fieldname: "hotel_zone", label: __("Zone"), fieldtype: "Data" },
			{ fieldname: "exact_position", label: __("Exact Position"), fieldtype: "Data" },
			{ fieldname: "remarks", label: __("Remarks"), fieldtype: "Text" },
		],
		tag: [
			{ fieldname: "rfid_tag", label: __("RFID Tag"), fieldtype: "Data", reqd: 1 },
			{ fieldname: "location_text", label: __("Location Text"), fieldtype: "Data" },
		],
		scope: [{ fieldname: "hotel_property", label: __("Hotel Property"), fieldtype: "Link", options: "Hotel Property", reqd: 1 }],
		findings: [
			{ fieldname: "inspect_all", label: __("Inspect All Assets in Scope"), fieldtype: "Check" },
			{ fieldname: "default_condition", label: __("Default Condition"), fieldtype: "Select", options: ["Good", "Fair", "Poor"], default: "Good" },
		],
	};

	shell();
	renderHome();
};
