frappe.ui.form.on("Fixed Asset", {
	refresh(frm) {
		frm.trigger("render_qr_code_image");
		frm.trigger("add_identifier_buttons");
		frm.trigger("add_core_maintenance_buttons");
		frm.trigger("bind_overview_media_gallery_hooks");
		frm.trigger("render_overview_media_gallery");
		frm.trigger("render_lifecycle_timeline");
		setTimeout(() => frm.trigger("render_qr_code_image"), 50);
		setTimeout(() => {
			frm.trigger("bind_overview_media_gallery_hooks");
			frm.trigger("render_overview_media_gallery");
		}, 120);
		setTimeout(() => frm.trigger("render_overview_media_gallery"), 380);
	},
	after_save(frm) {
		frm.trigger("render_qr_code_image");
		setTimeout(() => frm.trigger("render_overview_media_gallery"), 150);
	},
	qr_payload(frm) {
		frm.trigger("render_qr_code_image");
	},
	barcode(frm) {
		frm.trigger("render_qr_code_image");
	},
	internal_code(frm) {
		frm.trigger("render_qr_code_image");
	},
	asset_media_attachments_remove(frm) {
		frm.trigger("render_overview_media_gallery");
	},
	add_core_maintenance_buttons(frm) {
		if (frm.is_new()) return;
		if (!frappe.boot?.versions?.["erpgenex_maintenance_core"]) return;

		frm.add_custom_button(
			__("Core Work Order"),
			() => {
				frappe.route_options = {
					company: frm.doc.company,
					branch: frm.doc.branch,
					subject_doctype: "Fixed Asset",
					subject_name: frm.doc.name,
				};
				frappe.new_doc("Core Work Order");
			},
			__("Maintenance Core")
		);
	},
	add_identifier_buttons(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Generate / Refresh Codes"), () => {
			const code = (frm.doc.internal_code || frm.doc.name || "").trim();
			if (!code) return;

			if (!frm.doc.internal_code || frm.doc.internal_code !== code) {
				frm.set_value("internal_code", code);
			}
			if (!frm.doc.qr_payload || !frm.doc.qr_payload.trim()) {
				frm.set_value("qr_payload", code);
			}
			frm.set_value("barcode", code);
			frm.trigger("render_qr_code_image");
			frm.save();
		});

		frm.add_custom_button(__("Rebuild QR Image"), () => {
			frm.trigger("render_qr_code_image");
		});
	},
	render_qr_code_image(frm) {
		const payload = (
			(frm.doc.qr_payload || "").trim() ||
			(frm.doc.internal_code || "").trim() ||
			((frm.doc.name && !String(frm.doc.name).startsWith("new-fixed-asset-") ? frm.doc.name : "") || "").trim() ||
			(frm.doc.barcode || "").trim()
		);
		const $wrap = frm.fields_dict.qr_code_image?.$wrapper;
		if (!$wrap) return;
		if (!payload) {
			$wrap.html(`<div class="text-muted">${__("No QR payload")}</div>`);
			return;
		}
		frappe.call({
			method: "omnexa_fixed_assets.api.get_qr_svg_data_uri",
			args: { payload },
			callback: (r) => {
				const uri = r?.message?.data_uri;
				if (!uri) {
					$wrap.html(`<div class="text-muted">${__("Unable to generate QR code")}</div>`);
					return;
				}
				$wrap.html(
					`<div style="display:flex; gap:12px; align-items:center;">
						<img src="${uri}" style="width:120px; height:120px; border:1px solid #eee; border-radius:6px; padding:6px; background:#fff;" />
						<div class="text-muted" style="word-break:break-all;">${frappe.utils.escape_html(payload)}</div>
					</div>`
				);
			},
		});
	},

	bind_overview_media_gallery_hooks(frm) {
		if (frm._omnexa_overview_gallery_hooks) return;
		if (!frm.attachments) return;
		frm._omnexa_overview_gallery_hooks = true;
		const orig_refresh = frm.attachments.refresh.bind(frm.attachments);
		frm.attachments.refresh = function () {
			const ret = orig_refresh(...arguments);
			frm.trigger("render_overview_media_gallery");
			return ret;
		};
	},

	render_overview_media_gallery(frm) {
		const field = frm.fields_dict.overview_media_gallery;
		if (!field) return;

		const escape_attr = (s) =>
			String(s || "")
				.replace(/&/g, "&amp;")
				.replace(/"/g, "&quot;")
				.replace(/'/g, "&#39;")
				.replace(/</g, "&lt;");

		const attr_url = (u) => String(u || "").replace(/"/g, "&quot;");

		const normalize_path = (u) => {
			if (!u || typeof u !== "string") return "";
			let t = u.trim();
			const lower = t.toLowerCase();
			if (lower.startsWith("http://") || lower.startsWith("https://")) return t;
			if (!t.startsWith("/")) t = "/" + t;
			if (t.startsWith("/files/") || t.startsWith("/private/files/")) return t;
			return "";
		};

		const classify = (media_type, url) => {
			const mt = (media_type || "").trim().toLowerCase();
			if (mt === "image") return "image";
			if (mt === "video") return "video";
			if (mt === "document" || mt === "other") return "file";
			if (frappe.utils.is_image_file(url)) return "image";
			if (frappe.utils.is_video_file(url)) return "video";
			return "file";
		};

		const doc_icon = (url) => {
			const low = (url || "").split("?")[0].toLowerCase();
			if (low.endsWith(".pdf")) return "📄";
			if (low.endsWith(".doc") || low.endsWith(".docx")) return "📝";
			if (low.endsWith(".xls") || low.endsWith(".xlsx")) return "📊";
			return "📎";
		};

		const items = [];
		const seen = new Set();

		const push_item = (path, title, kind, badge) => {
			const norm = normalize_path(path);
			if (!norm) return;
			if (seen.has(norm)) return;
			seen.add(norm);
			const abs = frappe.urllib.get_full_url(norm);
			items.push({
				path: norm,
				url: abs,
				title: title || norm.split("/").pop() || __("File"),
				kind,
				badge,
			});
		};

		if (frappe.meta.has_field("Fixed Asset", "asset_media_attachments")) {
			(frm.doc.asset_media_attachments || []).forEach((row) => {
				const url = row.media_file;
				if (!url) return;
				const kind = classify(row.media_type, url);
				const title = row.caption || row.media_type || __("Media");
				push_item(url, title, kind, __("Media"));
			});
		}

		if (!frm.is_new() && frm.get_docinfo()?.attachments?.length) {
			for (const att of frm.get_docinfo().attachments) {
				const url = att.file_url || "";
				const kind = classify(null, url);
				const title = att.file_name || __("Attachment");
				push_item(url, title, kind, __("Attached"));
			}
		}

		let html = "";

		if (frm.is_new()) {
			html = `<div class="omnexa-fa-gallery">
				<p class="omnexa-fa-gallery__hint text-muted">${__(
					"Save the document to show photos and attachments here."
				)}</p></div>`;
		} else if (!items.length) {
			html = `<div class="omnexa-fa-gallery">
				<p class="omnexa-fa-gallery__hint text-muted">${__(
					"No photos or documents yet. Use the sidebar Attachments or add rows under Media Files (Hotel tab)."
				)}</p></div>`;
		} else {
			const cards = items
				.map((it, idx) => {
					const safe_cap = frappe.utils.escape_html(it.title);
					const badge = frappe.utils.escape_html(it.badge || "");
					const data_kind = escape_attr(it.kind);
					const data_url = attr_url(it.url);
					const data_title = escape_attr(it.title);

					if (it.kind === "image") {
						return `<button type="button" class="btn-reset omnexa-fa-gallery__card omnexa-fa-gallery__card--zoom"
							tabindex="0"
							data-idx="${idx}"
							data-kind="${data_kind}"
							data-url="${data_url}"
							data-title="${data_title}">
							<span class="omnexa-fa-gallery__thumb-wrap">
								<img class="omnexa-fa-gallery__thumb" alt="" loading="lazy"
									src="${attr_url(it.url)}" />
								<span class="omnexa-fa-gallery__badge">${badge}</span>
							</span>
							<span class="omnexa-fa-gallery__caption">${safe_cap}</span>
						</button>`;
					}

					if (it.kind === "video") {
						return `<button type="button" class="btn-reset omnexa-fa-gallery__card omnexa-fa-gallery__card--zoom"
							tabindex="0"
							data-idx="${idx}"
							data-kind="${data_kind}"
							data-url="${data_url}"
							data-title="${data_title}">
							<span class="omnexa-fa-gallery__thumb-wrap">
								<video class="omnexa-fa-gallery__thumb omnexa-fa-gallery__thumb--contain" muted preload="metadata"
									src="${attr_url(it.url)}"></video>
								<span class="omnexa-fa-gallery__video-play">▶</span>
								<span class="omnexa-fa-gallery__badge">${badge}</span>
							</span>
							<span class="omnexa-fa-gallery__caption">${safe_cap}<span class="omnexa-fa-gallery__meta">${__(
							"Video"
						)}</span></span>
						</button>`;
					}

					return `<button type="button" class="btn-reset omnexa-fa-gallery__card omnexa-fa-gallery__card--open"
						tabindex="0"
						data-idx="${idx}"
						data-kind="file"
						data-url="${data_url}"
						data-title="${data_title}">
						<span class="omnexa-fa-gallery__doc">
							<span class="omnexa-fa-gallery__doc-icon">${doc_icon(it.path)}</span>
							<span class="omnexa-fa-gallery__badge">${badge}</span>
						</span>
						<span class="omnexa-fa-gallery__caption">${safe_cap}<span class="omnexa-fa-gallery__meta">${__(
						"Click to open"
					)}</span></span>
					</button>`;
				})
				.join("");

			html = `<div class="omnexa-fa-gallery"><div class="omnexa-fa-gallery__grid">${cards}</div></div>`;
		}

		field.html(html);

		const $w = field.$wrapper;
		$w.off(".omnexaFaGal");
		$w.on("click.omnexaFaGal", ".omnexa-fa-gallery__card--zoom", function () {
			const url = $(this).attr("data-url");
			const title = $(this).attr("data-title") || "";
			const kind = ($(this).attr("data-kind") || "image").toLowerCase();
			open_preview(url, title, kind);
		});
		$w.on("keydown.omnexaFaGal", ".omnexa-fa-gallery__card--zoom", function (e) {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				$(this).trigger("click");
			}
		});
		$w.on("click.omnexaFaGal", ".omnexa-fa-gallery__card--open", function () {
			const url = $(this).attr("data-url");
			if (url) window.open(url, "_blank", "noopener,noreferrer");
		});

		function open_preview(url, title, kind) {
			if (!url) return;

			if (kind === "video") {
				const d = new frappe.ui.Dialog({
					title: frappe.utils.escape_html(title || __("Video")),
					size: "large",
					fields: [{ fieldtype: "HTML", fieldname: "omnexa_pv" }],
				});
				d.fields_dict.omnexa_pv.$wrapper.html(
					`<div style="text-align:center;background:#000;">
						<video controls autoplay style="max-width:100%;max-height:78vh;" src="${attr_url(url)}"></video>
					</div>`
				);
				d.show();
				return;
			}

			const safe_title = frappe.utils.escape_html(title || __("Preview"));
			const d = new frappe.ui.Dialog({
				title: safe_title,
				size: "extra-large",
				fields: [{ fieldtype: "HTML", fieldname: "omnexa_pv" }],
				primary_action_label: __("Close"),
				primary_action: () => d.hide(),
			});
			d.fields_dict.omnexa_pv.$wrapper.html(
				`<div style="text-align:center;padding:8px;background:var(--control-bg);">
					<img alt="" src="${attr_url(url)}"
						style="max-width:100%;max-height:78vh;object-fit:contain;border-radius:8px;" />
				</div>`
			);
			d.show();
		}
	},
	render_lifecycle_timeline(frm) {
		if (frm.is_new()) return;
		const field = frm.get_field("hotel_asset_section") || frm.get_field("eam_hierarchy_section");
		const anchor = field?.$wrapper || frm.layout?.wrapper;
		if (!anchor || !anchor.length) return;
		let $box = anchor.closest(".form-layout").find(".omnexa-lifecycle-timeline");
		if (!$box.length) {
			$box = $(`<div class="omnexa-lifecycle-timeline form-section"></div>`);
			anchor.closest(".form-section").after($box);
		}
		$box.html(`<div class="section-head">${__("Asset Lifecycle Timeline")}</div><div class="omnexa-lt-body text-muted">${__("Loading…")}</div>`);
		frappe.call({
			method: "omnexa_fixed_assets.api.get_asset_lifecycle_timeline",
			args: { asset: frm.doc.name, limit: 25 },
			callback(r) {
				const events = (r.message && r.message.events) || [];
				if (!events.length) {
					$box.find(".omnexa-lt-body").html(`<p class="text-muted">${__("No lifecycle events yet.")}</p>`);
					return;
				}
				const rows = events
					.map(
						(ev) => `<div class="omnexa-lt-row" style="padding:6px 0;border-bottom:1px solid var(--border-color);">
							<div><strong>${frappe.utils.escape_html(ev.event_type || "")}</strong>
							<span class="text-muted pull-right">${frappe.utils.escape_html(ev.date || "")}</span></div>
							<div>${frappe.utils.escape_html(ev.title || "")}</div>
						</div>`
					)
					.join("");
				$box.find(".omnexa-lt-body").html(rows);
			},
		});
	},
});

frappe.ui.form.on("Asset Media Attachment", {
	media_file(frm) {
		frm.trigger("render_overview_media_gallery");
	},
	media_type(frm) {
		frm.trigger("render_overview_media_gallery");
	},
	caption(frm) {
		frm.trigger("render_overview_media_gallery");
	},
});
