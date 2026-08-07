// Full-screen "what is this pump?" screen. Keyboard-first: type or scan a
// serial, press Enter, get identity + warranty + history + genealogy in one view.

frappe.pages["pump-lookup"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Pump Lookup"),
		single_column: true,
	});

	$(wrapper).find(".layout-main-section").append(`
		<div class="kl-wrap">
			<div class="kl-search">
				<input type="text" class="form-control kl-input"
					placeholder="${__("Scan or type a serial number, then press Enter")}" autofocus>
				<button class="btn btn-primary kl-go">${__("Look Up")}</button>
				<button class="btn btn-default kl-scan">${__("Scan")}</button>
			</div>
			<div class="kl-result"></div>
		</div>
		<style>
			.kl-wrap { max-width: 980px; margin: 0 auto; padding: 8px 0 40px; }
			.kl-search { display:flex; gap:10px; margin-bottom:22px; flex-wrap:wrap; }
			.kl-input { flex:1 1 320px; font-size:17px; height:44px; letter-spacing:0.5px; }
			.kl-search .btn { height:44px; }
			.kl-card { border:1px solid var(--border-color); border-radius:12px;
					   padding:20px; margin-bottom:16px; background:var(--fg-color); }
			.kl-head { display:flex; justify-content:space-between; align-items:flex-start;
					   flex-wrap:wrap; gap:12px; margin-bottom:14px; }
			.kl-sn { font-size:22px; font-weight:700; letter-spacing:0.5px; }
			.kl-model { color:var(--text-muted); font-size:14px; margin-top:2px; }
			.kl-badge { padding:9px 18px; border-radius:22px; font-weight:700; font-size:14px; }
			.kl-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:12px; }
			.kl-item { border:1px solid var(--border-color); border-radius:8px; padding:10px 12px; }
			.kl-lbl { font-size:11px; color:var(--text-muted); text-transform:uppercase;
					  letter-spacing:0.6px; }
			.kl-val { font-size:15px; font-weight:600; margin-top:3px; word-break:break-word; }
			.kl-actions { display:flex; gap:8px; flex-wrap:wrap; margin-top:6px; }
			.kl-h { font-size:13px; font-weight:700; text-transform:uppercase;
					letter-spacing:0.6px; color:var(--text-muted); margin:4px 0 10px; }
			.kl-empty { color:var(--text-muted); padding:28px 0; text-align:center; }
		</style>
	`);

	const $input = $(wrapper).find(".kl-input");
	const $result = $(wrapper).find(".kl-result");

	const lookup = () => {
		let sn = ($input.val() || "").trim();
		const m = sn.match(/[?&]sn=([^&]+)/);
		if (m) sn = decodeURIComponent(m[1]);
		if (!sn) return;

		$result.html(`<div class="kl-empty">${__("Looking up {0}...", [sn])}</div>`);
		frappe
			.call({ method: "kumar_service.api.get_pump_snapshot", args: { serial_no: sn } })
			.then((r) => render(r.message))
			.catch(() => {
				$result.html(
					`<div class="kl-card"><b>${__("Not found")}</b><div class="kl-model">${__(
						"No pump with serial {0}. Check the nameplate.",
						[sn]
					)}</div></div>`
				);
			});
	};

	$(wrapper).find(".kl-go").on("click", lookup);
	$input.on("keydown", (e) => {
		if (e.key === "Enter") lookup();
	});
	$(wrapper).find(".kl-scan").on("click", () => {
		new frappe.ui.Scanner({
			dialog: true,
			multiple: false,
			on_scan(data) {
				$input.val((data && (data.decodedText || data.result)) || "");
				lookup();
			},
		});
	});

	page.set_primary_action(__("Clear"), () => {
		$input.val("").focus();
		$result.empty();
	});

	function cell(label, value) {
		if (value === null || value === undefined || value === "") return "";
		return `<div class="kl-item"><div class="kl-lbl">${label}</div>
				<div class="kl-val">${frappe.utils.escape_html(String(value))}</div></div>`;
	}

	function render(s) {
		if (!s) return;

		let colour = "#6b7280", text = __("NOT REGISTERED");
		if (s.warranty_status === "In Warranty") { colour = "#137333"; text = __("IN WARRANTY"); }
		else if (s.warranty_status === "Expiring Soon") { colour = "#b06000"; text = __("EXPIRING SOON"); }
		else if (s.warranty_status === "Expired") { colour = "#a50e0e"; text = __("EXPIRED"); }

		const days =
			s.days_remaining !== null && s.days_remaining !== undefined
				? ` &middot; ${s.days_remaining} ${__("days")}`
				: "";

		$result.html(`
			<div class="kl-card">
				<div class="kl-head">
					<div>
						<div class="kl-sn">${frappe.utils.escape_html(s.serial_no)}</div>
						<div class="kl-model">${frappe.utils.escape_html(
							[s.model_code, s.category, s.hp ? s.hp + " HP" : "", s.phase]
								.filter(Boolean).join(" &middot; ")
						)}</div>
					</div>
					<div class="kl-badge" style="background:${colour}1a;color:${colour};border:1px solid ${colour}">
						${text}${days}
					</div>
				</div>

				<div class="kl-grid">
					${cell(__("Manufactured"), s.manufacturing_date)}
					${cell(__("QC Status"), s.qc_status)}
					${cell(__("BIS Standard"), s.bis_standard)}
					${cell(__("Impeller"), s.impeller_material)}
					${cell(__("RPM"), s.rpm)}
					${cell(__("Sold On"), s.sale_date)}
					${cell(__("Warranty Upto"), s.warranty_expiry_date)}
					${cell(__("Dealer"), s.dealer)}
					${cell(__("Customer"), s.end_customer_name)}
					${cell(__("Mobile"), s.end_customer_mobile)}
					${cell(__("Pincode"), s.installation_pincode)}
					${cell(__("Open Complaints"), s.open_complaints)}
				</div>

				<div class="kl-actions" style="margin-top:16px">
					<button class="btn btn-sm btn-primary kl-complaint">${__("Raise Complaint")}</button>
					${s.is_registered
						? `<button class="btn btn-sm btn-default kl-cert">${__("Warranty Certificate")}</button>`
						: `<button class="btn btn-sm btn-default kl-register">${__("Register Sale")}</button>`}
					<button class="btn btn-sm btn-default kl-trace">${__("Trace Genealogy")}</button>
					<button class="btn btn-sm btn-default kl-history">${__("Service History")}</button>
					<button class="btn btn-sm btn-default kl-open">${__("Open Serial")}</button>
				</div>
			</div>

			<div class="kl-card">
				<div class="kl-h">${__("Manufacturing Genealogy")}</div>
				<div class="kl-grid">
					${cell(__("Casing Heat"), s.heat_no)}
					${cell(__("Winding Batch"), s.winding_batch)}
					${cell(__("Rotor Batch"), s.rotor_batch)}
					${cell(__("Work Order"), s.work_order)}
					${cell(__("Test Certificate"), s.test_certificate)}
				</div>
			</div>

			<div class="kl-card">
				<div class="kl-h">${__("Service History")}</div>
				${kumar.history_html(s)}
				${s.is_repeat_failure
					? `<div style="margin-top:10px"><span class="indicator-pill orange">${__(
							"Repeat failure - reported more than once recently"
					  )}</span></div>`
					: ""}
			</div>
		`);

		$result.find(".kl-complaint").on("click", () =>
			frappe.new_doc("Service Request", { serial_no: s.serial_no }));
		$result.find(".kl-register").on("click", () =>
			frappe.new_doc("Pump Registration", { serial_no: s.serial_no }));
		$result.find(".kl-cert").on("click", () =>
			window.open(`/printview?doctype=Pump%20Registration&name=${encodeURIComponent(
				s.registration)}&format=KUMAR%20Warranty%20Certificate&no_letterhead=1`));
		$result.find(".kl-open").on("click", () =>
			frappe.set_route("Form", "Serial No", s.serial_no));
		$result.find(".kl-history").on("click", () =>
			frappe.set_route("List", "Service Request", { serial_no: s.serial_no }));
		$result.find(".kl-trace").on("click", () =>
			frappe.call({
				method: "kumar_service.traceability.trace_backward",
				args: { serial_no: s.serial_no },
				callback: (r) => kumar.show_genealogy(r.message),
			}));
	}

	// deep link: /app/pump-lookup?sn=KP-...
	const qs = frappe.utils.get_query_params();
	if (qs.sn) {
		$input.val(qs.sn);
		lookup();
	}
};
