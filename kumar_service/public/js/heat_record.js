frappe.ui.form.on("Heat Record", {
	refresh(frm) {
		if (frm.doc.spectro_readings && frm.doc.spectro_readings.length) {
			const out = frm.doc.spectro_readings.filter((r) => !r.within_spec);
			frm.dashboard.clear_headline();
			if (out.length) {
				frm.dashboard.set_headline(
					`<span class="indicator-pill red">${__("OUT OF SPEC: {0}", [
						out.map((r) => r.element).join(", "),
					])}</span>`
				);
			} else {
				frm.dashboard.set_headline(
					`<span class="indicator-pill green">${__("Chemistry within spec - CE {0}", [
						frm.doc.carbon_equivalent || "-",
					])}</span>`
				);
			}
		}

		if (!frm.is_new() && frm.doc.status === "Approved for Pouring") {
			frm.add_custom_button(__("Pumps From This Heat"), () => {
				frappe.set_route("List", "Serial No", { custom_heat_no: frm.doc.heat_no });
			});
			frm.add_custom_button(__("Batch Defect Analysis"), () => {
				frappe.set_route("query-report", "Batch Defect Analysis");
			});
		}

		if (frm.is_new() && !(frm.doc.spectro_readings || []).length) {
			frm.add_custom_button(__("Add Standard Elements"), () => {
				const spec = {
					C: [3.1, 3.6], Si: [1.8, 2.4], Mn: [0.5, 0.9],
					S: [0.02, 0.12], P: [0.02, 0.15], Cu: [0.1, 0.5],
				};
				Object.keys(spec).forEach((el) => {
					const row = frm.add_child("spectro_readings");
					row.element = el;
					row.spec_min = spec[el][0];
					row.spec_max = spec[el][1];
				});
				frm.refresh_field("spectro_readings");
			});
		}
	},
});
