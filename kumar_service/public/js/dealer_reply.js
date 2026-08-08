// "Reply to Dealer" on the two documents a dealer can raise.
//
// Staff can already type into the comment box at the bottom of the form, and
// that reaches the dealer's portal because the portal reads the same Comment
// thread. This button exists for the two things a bare comment cannot do:
//
//   1. record the reply as the SLA's first response, and
//   2. notify the dealer's portal login, so nobody has to keep checking.
//
// Shared by Service Request and Kumar Warranty Claim - the wiring at the bottom
// attaches it to both.

frappe.provide("kumar.reply");

kumar.reply.KIND = {
	"Service Request": "complaint",
	"Kumar Warranty Claim": "claim",
};

kumar.reply.CANNED = [
	__("A technician has been assigned and will visit within 24 hours."),
	__("This is covered by warranty. The visit and the part are free."),
	__("We need the pump brought to the service centre. Please arrange it."),
	__("Approved. A credit note will follow with your next statement."),
];

kumar.reply.dialog = function (frm) {
	const kind = kumar.reply.KIND[frm.doc.doctype];
	if (!kind) return;

	const is_request = frm.doc.doctype === "Service Request";
	const already_responded = is_request && frm.doc.first_response_on;

	const d = new frappe.ui.Dialog({
		title: __("Reply to {0}", [frm.doc.dealer || __("Dealer")]),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "canned",
				options:
					`<div style="margin-bottom:8px;font-size:12px;color:var(--text-muted)">` +
					__("Common replies - click to use one, then edit it.") +
					`</div><div class="kumar-canned" style="display:flex;gap:6px;flex-wrap:wrap">` +
					kumar.reply.CANNED.map(
						(c) =>
							`<button class="btn btn-xs btn-default kumar-can" style="text-align:left;white-space:normal">${frappe.utils.escape_html(
								c
							)}</button>`
					).join("") +
					`</div>`,
			},
			{
				fieldtype: "Small Text",
				fieldname: "message",
				label: __("Message to the dealer"),
				reqd: 1,
				description: __("They read this on a phone. Plain words, no jargon."),
			},
			{
				fieldtype: "Check",
				fieldname: "mark_responded",
				label: __("Record this as the first response for the SLA"),
				default: already_responded ? 0 : 1,
				depends_on: is_request ? undefined : "eval:false",
				description: already_responded
					? __("A first response is already recorded on this request.")
					: "",
			},
		],
		primary_action_label: __("Send to Dealer"),
		primary_action(values) {
			d.set_primary_action(__("Sending..."));
			d.disable_primary_action();
			frappe.call({
				method: "kumar_service.staff_api.reply_to_dealer",
				args: {
					kind: kind,
					name: frm.doc.name,
					message: values.message,
					mark_responded: values.mark_responded ? 1 : 0,
				},
				callback(r) {
					const res = r.message || {};
					d.hide();
					frappe.show_alert({ message: res.message, indicator: "green" });
					// first_response_on / sla_status were written straight to the row,
					// so the open form is stale until it is reloaded
					if (res.first_response_recorded) frm.reload_doc();
					else if (frm.timeline) frm.timeline.refresh();
				},
				error() {
					d.set_primary_action(__("Send to Dealer"));
					d.enable_primary_action();
				},
			});
		},
	});

	d.show();

	d.$wrapper.find(".kumar-can").on("click", function (e) {
		e.preventDefault();
		const field = d.get_field("message");
		const existing = field.get_value() || "";
		field.set_value((existing ? existing + " " : "") + $(this).text().trim());
	});
};

kumar.reply.attach = function (frm) {
	if (frm.is_new() || !frm.doc.dealer) return;
	frm.add_custom_button(__("Reply to Dealer"), () => kumar.reply.dialog(frm), __("Dealer"));

	// The nudge that makes the SLA real: an unanswered complaint says so on the
	// form, rather than only in a report somebody reads on Friday.
	if (frm.doc.doctype === "Service Request" && !frm.doc.first_response_on
		&& frm.doc.docstatus === 1 && frm.doc.status !== "Closed") {
		frm.dashboard.add_comment(
			__("This dealer has had no reply yet. Use Dealer &rarr; Reply to Dealer."),
			"orange",
			true
		);
	}
};

frappe.ui.form.on("Service Request", { refresh: kumar.reply.attach });
frappe.ui.form.on("Kumar Warranty Claim", { refresh: kumar.reply.attach });
