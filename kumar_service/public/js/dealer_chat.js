// The dealer conversation, as a chat panel on the document itself.
//
// Frappe's comment timeline technically carries this conversation, but it reads
// as an audit log: one column, system entries mixed in, and attachments buried.
// Staff answering a dealer want what they use everywhere else - Teams, Google
// Chat, WhatsApp: their own words on one side, the dealer's on the other,
// photographs inline, and a box at the bottom to type in.
//
// Writes through the same `staff_api.reply_to_dealer` as the Dealer Conversations
// queue, so the SLA first response is still recorded and the dealer is still
// notified, and the portal shows exactly the same thread.

frappe.provide("kumar.chat");

kumar.chat.KIND = {
	"Service Request": "complaint",
	"Kumar Warranty Claim": "claim",
};

kumar.chat.MAX_MB = 8;

kumar.chat.render = function (frm) {
	const kind = kumar.chat.KIND[frm.doc.doctype];
	if (!kind || frm.is_new() || !frm.doc.dealer) return;

	// add_section() appends, so a refresh would stack a second panel
	if (frm.__kumar_chat) {
		kumar.chat.load(frm);
		return;
	}

	const $section = frm.dashboard.add_section(
		`<div class="kchat">
			<div class="kchat-head">
				<div>
					<b class="kchat-with">${frappe.utils.escape_html(frm.doc.dealer)}</b>
					<span class="kchat-sub">${__("They see this in the dealer portal")}</span>
				</div>
				<button class="btn btn-xs btn-default kchat-refresh">${__("Refresh")}</button>
			</div>
			<div class="kchat-stream"><div class="kchat-loading">${__("Loading...")}</div></div>
			<div class="kchat-compose">
				<textarea class="form-control kchat-input" rows="2"
					placeholder="${__("Write to the dealer... they read this on a phone")}"></textarea>
				<div class="kchat-queued"></div>
				<div class="kchat-foot">
					<label class="kchat-attach">
						&#128206; ${__("Attach")}
						<input type="file" multiple accept="image/*,application/pdf">
					</label>
					<label class="kchat-sla">
						<input type="checkbox" checked> ${__("Record as first response")}
					</label>
					<button class="btn btn-sm btn-primary kchat-send">${__("Send")}</button>
				</div>
			</div>
		</div>`,
		__("Conversation with Dealer")
	);

	frm.__kumar_chat = $section;
	kumar.chat.wire(frm, $section);
	kumar.chat.load(frm);
};

kumar.chat.wire = function (frm, $section) {
	const kind = kumar.chat.KIND[frm.doc.doctype];
	const queued = [];
	const $queue = $section.find(".kchat-queued");
	const $input = $section.find(".kchat-input");

	const drawQueue = () => {
		$queue.html(
			queued
				.map(
					(q, i) =>
						`<span class="kchat-file">${frappe.utils.escape_html(q.filename)}<b data-drop="${i}">&times;</b></span>`
				)
				.join("")
		);
		$queue.find("[data-drop]").on("click", function () {
			queued.splice(parseInt($(this).data("drop"), 10), 1);
			drawQueue();
		});
	};

	$section.find(".kchat-attach input").on("change", function () {
		const files = Array.from(this.files || []);
		const input = this;
		let pending = files.length;
		const done = () => {
			if (--pending <= 0) {
				input.value = "";
				drawQueue();
			}
		};
		files.forEach((file) => {
			if (file.size > kumar.chat.MAX_MB * 1024 * 1024) {
				frappe.show_alert({
					message: __("{0} is too large. The limit is {1} MB.", [
						file.name,
						kumar.chat.MAX_MB,
					]),
					indicator: "red",
				});
				done();
				return;
			}
			const fr = new FileReader();
			fr.onload = () => {
				queued.push({
					filename: file.name,
					content: String(fr.result).split(",")[1] || "",
				});
				done();
			};
			fr.onerror = done;
			fr.readAsDataURL(file);
		});
	});

	$section.find(".kchat-refresh").on("click", () => kumar.chat.load(frm));

	const send = () => {
		const message = ($input.val() || "").trim();
		// an attachment on its own is a valid reply
		if (!message && !queued.length) return;
		const $btn = $section.find(".kchat-send");
		$btn.prop("disabled", true).text(__("Sending..."));

		frappe.call({
			method: "kumar_service.staff_api.reply_to_dealer",
			args: {
				kind: kind,
				name: frm.doc.name,
				message: message,
				mark_responded: $section.find(".kchat-sla input").is(":checked") ? 1 : 0,
				attachments: JSON.stringify(queued),
			},
			callback(r) {
				const d = r.message || {};
				$input.val("");
				queued.length = 0;
				drawQueue();
				$btn.prop("disabled", false).text(__("Send"));
				kumar.chat.draw(frm, $section, d.thread || []);
				frappe.show_alert({ message: d.message, indicator: "green" });
				// first_response_on and sla_status were written straight to the row,
				// so the open form is stale until it is reloaded
				if (d.first_response_recorded) frm.reload_doc();
			},
			error() {
				$btn.prop("disabled", false).text(__("Send"));
			},
		});
	};

	$section.find(".kchat-send").on("click", send);
	$input.on("keydown", function (e) {
		// Enter sends, Shift+Enter makes a new line - the convention everywhere
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			send();
		}
	});
};

kumar.chat.load = function (frm) {
	const $section = frm.__kumar_chat;
	if (!$section) return;
	frappe.call({
		method: "kumar_service.staff_api.conversation",
		args: { kind: kumar.chat.KIND[frm.doc.doctype], name: frm.doc.name },
		callback(r) {
			kumar.chat.draw(frm, $section, (r.message || {}).thread || []);
		},
		error() {
			$section
				.find(".kchat-stream")
				.html(`<div class="kchat-empty">${__("Not permitted")}</div>`);
		},
	});
};

kumar.chat.draw = function (frm, $section, thread) {
	const esc = frappe.utils.escape_html;
	const $stream = $section.find(".kchat-stream");

	if (!thread.length) {
		$stream.html(
			`<div class="kchat-empty">${__("Nothing said yet. Write below and the dealer sees it in the portal.")}</div>`
		);
		return;
	}

	const files = (list) =>
		!list || !list.length
			? ""
			: `<div class="kchat-atts">` +
				list
					.map((a) =>
						a.is_image
							? `<a href="${esc(a.file_url)}" target="_blank" rel="noopener"
									title="${esc(a.file_name)}"><img src="${esc(a.file_url)}" alt=""></a>`
							: `<a href="${esc(a.file_url)}" target="_blank" rel="noopener"
									class="kchat-doc">&#128206; ${esc(a.file_name)}</a>`
					)
					.join("") +
				`</div>`;

	const when = (v) =>
		v && frappe.datetime.comment_when ? frappe.datetime.comment_when(v) : esc(v || "");

	$stream.html(
		thread
			.map(
				(m) => `
		<div class="kchat-row ${m.from_dealer ? "in" : "out"}">
			<div class="kchat-bub">
				<div class="kchat-who">${esc(m.from_dealer ? __("Dealer") : "KUMAR")}
					&middot; ${esc(m.by || "")} &middot; ${when(m.on)}</div>
				<div class="kchat-text">${esc(m.message)}</div>
				${files(m.attachments)}
			</div>
		</div>`
			)
			.join("")
	);

	// a chat opens at the newest message, not the oldest
	const node = $stream[0];
	if (node) node.scrollTop = node.scrollHeight;
};

frappe.ui.form.on("Service Request", { refresh: kumar.chat.render });
frappe.ui.form.on("Kumar Warranty Claim", { refresh: kumar.chat.render });
