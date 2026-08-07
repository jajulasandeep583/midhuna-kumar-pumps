frappe.ui.form.on("Kumar Warranty Claim", {
	refresh(frm) {
		if (frm.doc.serial_no && !frm.is_new()) {
			frm.add_custom_button(__("Trace Genealogy"), () => {
				frappe.call({
					method: "kumar_service.traceability.trace_backward",
					args: { serial_no: frm.doc.serial_no },
					callback: (r) => kumar.show_genealogy(r.message),
				});
			});
		}

		if (frm.doc.heat_no || frm.doc.winding_batch) {
			frm.add_custom_button(__("Other Pumps From This Batch"), () => {
				frappe.call({
					method: "kumar_service.traceability.trace_forward",
					args: { batch_no: frm.doc.heat_no || frm.doc.winding_batch },
					callback: (r) => {
						const d = r.message || {};
						const colour = d.above_threshold ? "red" : "green";
						new frappe.ui.Dialog({
							title: __("Batch {0}", [d.batch_no]),
							fields: [
								{
									fieldtype: "HTML",
									options: `<div>
										<p><span class="indicator-pill ${colour}">${__("Failure rate {0}% (threshold {1}%)", [
										d.failure_rate_pct,
										d.threshold_pct,
									])}</span></p>
										<p>${__("{0} units built, {1} registered, {2} with complaints.", [
											d.total_units,
											d.registered,
											d.with_complaints,
										])}</p>
									</div>`,
								},
							],
						}).show();
					},
				});
			});
		}

		if (frm.doc.docstatus === 1 && frm.doc.workflow_state) {
			frm.dashboard.clear_headline();
			frm.dashboard.set_headline(
				`<span class="indicator-pill blue">${__("Claim status: {0}", [frm.doc.workflow_state])}</span>`
			);
		}
	},
});
