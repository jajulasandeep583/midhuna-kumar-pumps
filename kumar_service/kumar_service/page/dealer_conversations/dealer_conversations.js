// KUMAR's side of the dealer portal: answer the dealers.
//
// The service manager's actual job here is a queue, not a dashboard: who is
// waiting on us, oldest first, and let me answer without opening sixty
// documents. So the default view is "Waiting on KUMAR" and every row carries a
// reply box inline.
//
// Staff can still reply from the comment box on the Service Request form - this
// screen writes to the same thread, so both routes and the dealer's portal all
// read the same conversation.

frappe.pages["dealer-conversations"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Dealer Conversations"),
		single_column: true,
	});

	const $main = $(wrapper).find(".layout-main-section");
	const $body = $('<div class="kv-wrap"></div>');
	$main.append($body);

	const state = { dealer: null, view: "waiting", search: "" };
	let latest = null;

	// ---------------------------------------------------------------- filters
	const dealer_field = page.add_field({
		fieldname: "dealer",
		label: __("Dealer"),
		fieldtype: "Link",
		options: "Dealer",
		change() {
			state.dealer = dealer_field.get_value() || null;
			load();
		},
	});

	const view_field = page.add_field({
		fieldname: "view",
		label: __("Show"),
		fieldtype: "Select",
		default: "waiting",
		options: [
			{ value: "waiting", label: __("Waiting on KUMAR") },
			{ value: "open", label: __("All Open") },
			{ value: "answered", label: __("Answered") },
			{ value: "silent", label: __("No Conversation Yet") },
			{ value: "all", label: __("Everything") },
		],
		change() {
			state.view = view_field.get_value() || "waiting";
			load();
		},
	});

	const search_field = page.add_field({
		fieldname: "search",
		label: __("Search"),
		fieldtype: "Data",
		change() {
			state.search = search_field.get_value() || "";
			load();
		},
	});

	page.set_secondary_action(__("Refresh"), load);

	page.add_menu_item(__("Open Service Request List"), () =>
		frappe.set_route("List", "Service Request"));
	page.add_menu_item(__("Dealer Requests and Claims report"), () =>
		frappe.set_route("query-report", "Dealer Requests and Claims"));

	// ------------------------------------------------------------------ load
	function load() {
		$body.html(`<div class="kv-load">${__("Loading...")}</div>`);
		frappe.call({
			method: "kumar_service.staff_api.dealer_conversations",
			args: {
				dealer: state.dealer,
				state: state.view,
				search: state.search,
			},
			callback(r) {
				latest = r.message;
				render(latest);
			},
			error() {
				$body.html(
					`<div class="kv-empty">${__("Could not load this screen. You may not have permission for it.")}</div>`
				);
			},
		});
	}

	const esc = frappe.utils.escape_html;
	const money = (v) => format_currency(v, "INR");

	function when(value) {
		if (!value) return "";
		return frappe.datetime.comment_when
			? frappe.datetime.comment_when(value)
			: frappe.datetime.str_to_user(value);
	}

	// ---------------------------------------------------------------- render
	function render(d) {
		if (!d) return;
		const s = d.summary || {};

		const tiles = [
			["waiting", __("Waiting on KUMAR"), s.waiting, "kv-red"],
			["late", __("Past the promised date"), s.late, "kv-amber"],
			["answered", __("Answered"), s.answered, "kv-green"],
			["silent", __("No reply either way"), s.silent, "kv-grey"],
			["total", __("On this list"), s.total, "kv-blue"],
		]
			.map(
				([, label, value, cls]) => `
			<div class="kv-tile ${cls}">
				<b>${cint(value)}</b><span>${esc(label)}</span>
			</div>`
			)
			.join("");

		const dealer_rows = (d.dealers || [])
			.slice(0, 12)
			.map(
				(row) => `
			<tr data-dealer="${esc(row.dealer)}" class="kv-dealer-row">
				<td><b>${esc(row.dealer)}</b></td>
				<td class="kv-num">${cint(row.total)}</td>
				<td class="kv-num">${row.waiting ? `<span class="kv-pill red">${cint(row.waiting)}</span>` : "0"}</td>
				<td class="kv-num">${row.late ? `<span class="kv-pill amber">${cint(row.late)}</span>` : "0"}</td>
			</tr>`
			)
			.join("");

		const cards = (d.tickets || []).map(ticket_card).join("");

		$body.html(`
			<div class="kv-tiles">${tiles}</div>

			${
				dealer_rows
					? `<div class="kv-panel">
					<div class="kv-h">${__("Who Is Waiting")}</div>
					<div class="kv-hint">${__("Click a dealer to see only their tickets.")}</div>
					<table class="kv-t">
						<thead><tr>
							<th>${__("Dealer")}</th><th class="kv-num">${__("Tickets")}</th>
							<th class="kv-num">${__("Waiting")}</th><th class="kv-num">${__("Late")}</th>
						</tr></thead>
						<tbody>${dealer_rows}</tbody>
					</table>
				</div>`
					: ""
			}

			<div class="kv-panel">
				<div class="kv-h">${__("Tickets")}</div>
				<div class="kv-hint">${__("Whoever KUMAR owes a reply to comes first. Replying records the first response against the SLA.")}</div>
				${cards || `<div class="kv-empty">${__("Nothing here. Every dealer has been answered.")}</div>`}
			</div>
		`);

		$body.find(".kv-dealer-row").on("click", function () {
			dealer_field.set_value($(this).data("dealer"));
		});

		wire_cards();
	}

	function ticket_card(t) {
		const tone =
			t.conversation === "waiting" ? "red" : t.conversation === "answered" ? "green" : "grey";
		const convo_label =
			t.conversation === "waiting"
				? __("Waiting on KUMAR")
				: t.conversation === "answered"
				? __("Answered")
				: __("No reply yet");

		return `
		<div class="kv-card kv-${tone}" data-kind="${esc(t.kind)}" data-name="${esc(t.name)}">
			<div class="kv-card-top">
				<div>
					<div class="kv-meta">
						${t.kind === "claim" ? __("Warranty Claim") : __("Complaint")} &middot;
						<a href="/app/${t.kind === "claim" ? "kumar-warranty-claim" : "service-request"}/${encodeURIComponent(t.name)}">${esc(t.name)}</a>
					</div>
					<div class="kv-title">${esc(__(t.headline || "") || t.name)}</div>
					<div class="kv-sub">
						<b>${esc(t.dealer || "")}</b>
						${t.serial_no ? " &middot; " + esc(t.serial_no) : ""}
						${t.pump_model ? " &middot; " + esc(t.pump_model) : ""}
						${t.customer ? "<br>" + esc(t.customer) : ""}
						${t.mobile ? ` &middot; <a href="tel:${esc(t.mobile)}">${esc(t.mobile)}</a>` : ""}
						${t.amount ? " &middot; " + money(t.amount) : ""}
					</div>
					${t.detail ? `<div class="kv-said">${esc(String(t.detail).slice(0, 260))}</div>` : ""}
				</div>
				<div class="kv-right">
					<span class="kv-pill ${tone}">${esc(convo_label)}</span>
					<span class="kv-pill grey">${esc(__(t.status || ""))}</span>
					${t.late ? `<span class="kv-pill amber">${__("Late")}</span>` : ""}
					${t.free ? `<span class="kv-pill green">${__("In warranty")}</span>` : ""}
					<div class="kv-when">${esc(when(t.on))}</div>
				</div>
			</div>

			${
				t.last_message
					? `<div class="kv-last">
						<b>${t.conversation === "waiting" ? __("Dealer") : "KUMAR"}:</b>
						${esc(t.last_message)}
						<span class="kv-when">${esc(when(t.last_on))}</span>
					</div>`
					: ""
			}

			<div class="kv-actions">
				<button class="btn btn-xs btn-default kv-thread">
					${t.replies ? __("Conversation ({0})", [cint(t.replies)]) : __("Start a conversation")}
				</button>
				<button class="btn btn-xs btn-primary kv-reply-open">${__("Reply to Dealer")}</button>
			</div>
			<div class="kv-thread-box"></div>
			<div class="kv-reply-box"></div>
		</div>`;
	}

	// ------------------------------------------------------------ interaction
	function wire_cards() {
		$body.find(".kv-card").each(function () {
			const $card = $(this);
			const kind = $card.data("kind");
			const name = $card.data("name");

			$card.find(".kv-thread").on("click", function () {
				const $box = $card.find(".kv-thread-box");
				if ($box.data("open")) {
					$box.empty().data("open", false);
					return;
				}
				$box.html(`<div class="kv-load">${__("Loading...")}</div>`).data("open", true);
				frappe.call({
					method: "kumar_service.staff_api.conversation",
					args: { kind, name },
					callback(r) {
						draw_thread($box, (r.message || {}).thread || []);
					},
				});
			});

			$card.find(".kv-reply-open").on("click", function () {
				const $box = $card.find(".kv-reply-box");
				if ($box.data("open")) {
					$box.empty().data("open", false);
					return;
				}
				$box.data("open", true).html(`
					<div class="kv-reply">
						<textarea class="form-control kv-msg" rows="3"
							placeholder="${__("What should the dealer be told? Plain words - they read this on a phone.")}"></textarea>
						<div class="kv-queued"></div>
						<div class="kv-reply-foot">
							<label class="kv-check">
								<input type="checkbox" class="kv-sla" checked>
								${__("Record this as the first response for the SLA")}
							</label>
							<div style="display:flex;gap:10px;align-items:center">
								<label class="kv-pickfile">
									&#128206; ${__("Attach")}
									<input type="file" class="kv-file" multiple accept="image/*,application/pdf">
								</label>
								<button class="btn btn-sm btn-primary kv-send">${__("Send to Dealer")}</button>
							</div>
						</div>
						<div class="kv-canned">
							${[
								__("A technician has been assigned and will visit within 24 hours."),
								__("This is covered by warranty. The visit and the part are free."),
								__("We need the pump brought to the service centre. Please arrange it."),
								__("Approved. A credit note will follow with your next statement."),
							]
								.map((c) => `<button class="btn btn-xs btn-default kv-can">${esc(c)}</button>`)
								.join("")}
						</div>
					</div>`);

				// Attach a credit note or an inspection photo. Read in the browser
				// and posted with the message, so there is no half-finished upload
				// to clean up if the reply is abandoned.
				const queued = [];
				const $queue = $box.find(".kv-queued");
				const drawQueue = () => {
					$queue.html(
						queued.map((q, i) =>
							`<span class="kv-qfile">${esc(q.filename)}<b data-drop="${i}">&times;</b></span>`
						).join("")
					);
					$queue.find("[data-drop]").on("click", function () {
						queued.splice(parseInt($(this).data("drop"), 10), 1);
						drawQueue();
					});
				};
				$box.find(".kv-file").on("change", function () {
					const files = Array.from(this.files || []);
					const input = this;
					let pending = files.length;
					files.forEach((file) => {
						if (file.size > 8 * 1024 * 1024) {
							frappe.show_alert({
								message: __("{0} is too large. The limit is {1} MB.", [file.name, 8]),
								indicator: "red",
							});
							if (--pending === 0) { input.value = ""; drawQueue(); }
							return;
						}
						const fr = new FileReader();
						fr.onload = () => {
							queued.push({
								filename: file.name,
								content: String(fr.result).split(",")[1] || "",
							});
							if (--pending === 0) { input.value = ""; drawQueue(); }
						};
						fr.onerror = () => {
							if (--pending === 0) { input.value = ""; drawQueue(); }
						};
						fr.readAsDataURL(file);
					});
				});

				// Canned lines, because a service desk answers the same four
				// questions all day and typing them out is what stops people replying.
				$box.find(".kv-can").on("click", function () {
					const $msg = $box.find(".kv-msg");
					const existing = $msg.val();
					$msg.val((existing ? existing + " " : "") + $(this).text().trim()).focus();
				});

				$box.find(".kv-send").on("click", function () {
					const $btn = $(this);
					const message = $box.find(".kv-msg").val();
					// an attachment on its own is a valid reply - a credit note needs
					// no covering letter
					if (!(message || "").trim() && !queued.length) {
						frappe.show_alert({ message: __("Write a message before sending"), indicator: "orange" });
						return;
					}
					$btn.prop("disabled", true).text(__("Sending..."));
					frappe.call({
						method: "kumar_service.staff_api.reply_to_dealer",
						args: {
							kind,
							name,
							message,
							mark_responded: $box.find(".kv-sla").is(":checked") ? 1 : 0,
							attachments: JSON.stringify(queued),
						},
						callback(r) {
							const d = r.message || {};
							frappe.show_alert({ message: d.message, indicator: "green" });
							$box.empty().data("open", false);
							draw_thread($card.find(".kv-thread-box").data("open", true), d.thread || []);
							// the queue itself has changed - this ticket is no longer waiting
							setTimeout(load, 900);
						},
						error() {
							$btn.prop("disabled", false).text(__("Send to Dealer"));
						},
					});
				});
			});
		});
	}

	function draw_thread($box, thread) {
		if (!thread.length) {
			$box.html(`<div class="kv-empty small">${__("Nothing said yet.")}</div>`);
			return;
		}
		const files = (list) =>
			!list || !list.length
				? ""
				: `<div class="kv-atts">` +
					list
						.map((a) =>
							a.is_image
								? `<a class="kv-att" href="${esc(a.file_url)}" target="_blank"
										rel="noopener" title="${esc(a.file_name)}">
										<img src="${esc(a.file_url)}" alt=""></a>`
								: `<a class="kv-att" href="${esc(a.file_url)}" target="_blank"
										rel="noopener">&#128206; ${esc(a.file_name)}</a>`
						)
						.join("") +
					`</div>`;

		$box.html(
			`<div class="kv-msgs">` +
				thread
					.map(
						(m) => `
				<div class="kv-bubble ${m.from_dealer ? "dealer" : "kumar"}">
					<div class="kv-bubble-who">${esc(m.from_dealer ? __("Dealer") : "KUMAR")}
						&middot; ${esc(m.by || "")} &middot; ${esc(when(m.on))}</div>
					<div>${esc(m.message)}</div>
					${files(m.attachments)}
				</div>`
					)
					.join("") +
				`</div>`
		);
	}

	load();
};
