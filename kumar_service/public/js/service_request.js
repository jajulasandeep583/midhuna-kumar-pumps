// Type a serial, get the whole pump. This is the form the service desk lives in.

frappe.ui.form.on("Service Request", {
	refresh(frm) {
		kumar.scan_serial(frm);
		if (frm.doc.serial_no) render(frm);

		if (!frm.is_new() && frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Service Visit"), () => {
				frappe.new_doc("Service Visit", {
					service_request: frm.doc.name,
					serial_no: frm.doc.serial_no,
					technician: frm.doc.assigned_technician,
					is_chargeable: frm.doc.is_under_warranty ? 0 : 1,
				});
			}, __("Create"));

			if (!frm.doc.linked_claim && frm.doc.is_under_warranty) {
				frm.add_custom_button(__("Warranty Claim"), () => {
					frappe.new_doc("Kumar Warranty Claim", {
						service_request: frm.doc.name,
						serial_no: frm.doc.serial_no,
						dealer: frm.doc.dealer,
						root_cause: frm.doc.root_cause,
					});
				}, __("Create"));
			}

			frm.add_custom_button(__("Trace Genealogy"), () => {
				frappe.call({
					method: "kumar_service.traceability.trace_backward",
					args: { serial_no: frm.doc.serial_no },
					callback: (r) => kumar.show_genealogy(r.message),
				});
			});
		}
	},

	serial_no(frm) {
		render(frm);
	},
});

function render(frm) {
	if (!frm.doc.serial_no) return;

	kumar.fetch_snapshot(frm, frm.doc.serial_no).then((snap) => {
		if (!snap) return;

		frm.set_value({
			pump_model: snap.pump_model,
			hp: snap.hp,
			phase: snap.phase,
			manufacturing_date: snap.manufacturing_date,
			dealer: snap.dealer,
			sale_date: snap.sale_date,
			warranty_expiry_date: snap.warranty_expiry_date,
			end_customer_name: snap.end_customer_name,
			end_customer_mobile: snap.end_customer_mobile,
			is_under_warranty: snap.is_under_warranty ? 1 : 0,
			is_repeat_failure: snap.is_repeat_failure ? 1 : 0,
		});

		kumar.warranty_banner(frm, snap);
		frm.get_field("service_history_html").$wrapper.html(kumar.history_html(snap));

		const badge = snap.is_under_warranty
			? `<span class="indicator-pill green">${__("Warranty job - not chargeable")}</span>`
			: `<span class="indicator-pill red">${__("Out of warranty - chargeable")}</span>`;
		frm.get_field("warranty_status_html").$wrapper.html(
			`<div style="padding:6px 0">${badge}</div>`
		);
	});
}

kumar.show_genealogy = function (data) {
	if (!data) return;
	const row = (k, v) => (v ? `<tr><td><b>${k}</b></td><td>${frappe.utils.escape_html(String(v))}</td></tr>` : "");
	const heat = data.heat || {};
	const wind = data.winding || {};
	const cert = data.test_certificate || {};

	const html = `<table class="table table-bordered table-sm">
		${row(__("Serial"), data.serial_no)}
		${row(__("Model"), data.pump_model)}
		${row(__("Manufactured"), data.manufacturing_date)}
		${row(__("Work Order"), data.work_order)}
		${row(__("QC Status"), data.qc_status)}
		${row(__("Casing Heat"), data.heat_batch)}
		${row(__("Heat Grade"), heat.grade_achieved || heat.target_grade)}
		${row(__("Carbon Equivalent"), heat.carbon_equivalent)}
		${row(__("Winding Batch"), data.winding_batch)}
		${row(__("Wire Gauge"), wind.wire_gauge_swg)}
		${row(__("IR Test (Mohm)"), wind.ir_test_mohm)}
		${row(__("Rotor Batch"), data.rotor_batch)}
		${row(__("Test Certificate"), cert.name)}
		${row(__("Test Result"), cert.overall_result)}
	</table>`;

	new frappe.ui.Dialog({
		title: __("Genealogy: {0}", [data.serial_no]),
		size: "large",
		fields: [{ fieldtype: "HTML", options: html }],
	}).show();
};
