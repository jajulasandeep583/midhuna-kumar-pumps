// Copyright (c) 2026, MIDHUNATECH and contributors
// For license information, please see license.txt

frappe.ui.form.on("Winding Batch Record", {
	refresh(frm) {
		if (frm.is_new()) return;

		const passed = frm.doc.qty_passed || frm.doc.qty_produced || 0;
		if (frm.doc.qty_rejected) {
			frm.dashboard.set_headline(
				`<span class="indicator-pill orange">${__("{0} passed, {1} rejected", [
					passed,
					frm.doc.qty_rejected,
				])}</span>`
			);
		} else if (passed) {
			frm.dashboard.set_headline(
				`<span class="indicator-pill green">${__("{0} stators passed - IR {1} MΩ, HiPot {2} kV", [
					passed,
					frm.doc.ir_test_mohm || "-",
					frm.doc.hipot_test_kv || "-",
				])}</span>`
			);
		}

		// The winding run itself: copper, insulation and varnish out of Stores,
		// stators back in under a Batch named after this record. Without it the
		// stators would appear in stock from nowhere and the copper would be
		// bought and never issued - the same hole the foundry used to have.
		if (passed) {
			frm.add_custom_button(__("Make Winding Entry"), () => {
				frappe.call({
					method: "kumar_service.shopfloor.make_winding_entry",
					args: { winding_record: frm.doc.name },
					freeze: true,
					freeze_message: __("Winding..."),
					callback: (r) => {
						if (r.message) frappe.set_route("Form", "Stock Entry", r.message);
					},
				});
			}).addClass("btn-primary");
		}

		if (frm.doc.batch_no) {
			frm.add_custom_button(__("Pumps From This Lot"), () => {
				frappe.set_route("List", "Serial No", { custom_winding_batch: frm.doc.batch_no });
			});
		}
	},
});
