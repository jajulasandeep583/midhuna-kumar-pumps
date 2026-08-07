// The dealer's own screen.
//
// A dealer is not a head-office analyst. They are standing in a shop with a
// customer in front of them, usually on a phone. So this screen deliberately
// does the opposite of the network view:
//
//   - one headline number, not twelve tiles
//   - big buttons for the two things they actually do (register a sale,
//     raise a complaint) instead of a menu
//   - lists with a tap-to-call, not sortable tables
//   - weeks, not days, because four bars read on a phone and thirty do not
//   - plain words: "pumps you sold", not "registrations MTD"

frappe.pages["my-business"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("My Business"),
		single_column: true,
	});

	const $main = $(wrapper).find(".layout-main-section");
	const $body = $('<div class="kc-wrap"></div>');
	$main.append($body);

	// One simple period switch. No date pickers - a dealer does not want to
	// type two dates to find out how the month is going.
	let period = "this_month";

	page.set_primary_action(__("Register a Pump"), () =>
		frappe.new_doc("Pump Registration")
	);

	page.add_menu_item(__("This Month"), () => switch_to("this_month"));
	page.add_menu_item(__("Last 30 Days"), () => switch_to("last_30"));
	page.add_menu_item(__("Last Month"), () => switch_to("last_month"));
	page.add_menu_item(__("This Financial Year"), () => switch_to("this_year"));

	function switch_to(key) {
		period = key;
		load();
	}

	function load() {
		const [from_date, to_date] = kumar.dash.resolve_preset(period);
		kumar.dash.load(
			$body,
			"kumar_service.dashboard.dealer_cockpit",
			{ from_date, to_date },
			render
		);
	}

	function label_for_period() {
		const found = kumar.dash.PRESETS.find((p) => p.key === period);
		return found ? found.label : __("This Month");
	}

	function render(d) {
		const t = d.tiles || {};
		const num = kumar.dash.num;

		$body.html(`
			<div class="kc-hello">${__("Welcome back")}</div>
			<div class="kc-name">${kumar.dash.esc(d.dealer_name || __("KUMAR Dealer"))}</div>

			<div class="kc-headline">
				<div class="kc-headline-label">${__("Pumps you sold")} &middot; ${label_for_period()}</div>
				<div class="kc-headline-value">${num(t.units)}</div>
				<div class="kc-headline-sub" id="mb-compare"></div>
			</div>

			<div class="kc-tiles" id="mb-tiles"></div>

			<div class="kc-actions">
				<button class="kc-action kc-primary" data-act="register">
					<span class="kc-ico">+</span>${__("Register a Sale")}
				</button>
				<button class="kc-action" data-act="complaint">
					<span class="kc-ico">!</span>${__("Raise a Complaint")}
				</button>
				<button class="kc-action" data-act="lookup">
					<span class="kc-ico">&#9906;</span>${__("Check a Pump")}
				</button>
				<button class="kc-action" data-act="claims">
					<span class="kc-ico">&#8942;</span>${__("My Claims")}
				</button>
			</div>

			<div class="kc-block">
				<div class="kc-block-title">${__("How your weeks went")}</div>
				<div class="kc-block-sub">${__("Pumps sold each week")}</div>
				<div class="kc-week" id="mb-week"></div>
			</div>

			<div class="kc-block">
				<div class="kc-block-title">${__("Jobs waiting on you")}</div>
				<div class="kc-block-sub">${__(
					"Complaints from your customers that are still open"
				)}</div>
				<div id="mb-jobs"></div>
			</div>

			<div class="kc-block">
				<div class="kc-block-title">${__("Call these customers")}</div>
				<div class="kc-block-sub">${__(
					"Their warranty ends soon - a good moment to offer a service or a new pump"
				)}</div>
				<div id="mb-expiring"></div>
			</div>

			<div class="kc-block">
				<div class="kc-block-title">${__("Your recent sales")}</div>
				<div class="kc-block-sub">${__("The last pumps you registered")}</div>
				<div id="mb-recent"></div>
			</div>
		`);

		// ---- comparison, in words rather than a percentage badge
		const $cmp = $body.find("#mb-compare");
		if (t.previous_units) {
			const diff = t.units - t.previous_units;
			if (diff > 0) {
				$cmp.text(
					__("{0} more than the period before ({1})", [diff, num(t.previous_units)])
				);
			} else if (diff < 0) {
				$cmp.text(
					__("{0} fewer than the period before ({1})", [
						Math.abs(diff),
						num(t.previous_units),
					])
				);
			} else {
				$cmp.text(__("Same as the period before"));
			}
		} else {
			$cmp.text(__("Sales value {0}", [kumar.dash.money(t.revenue)]));
		}

		// ---- four numbers, no more
		$body.find("#mb-tiles").html(
			[
				{
					value: kumar.dash.money(t.revenue),
					label: __("Sales value"),
					title: kumar.dash.rupees(t.revenue),
				},
				{
					value: num(t.open_jobs),
					label: __("Open complaints"),
					tone: t.open_jobs > 0 ? "kc-alert" : "kc-good",
					route: "/app/service-request",
				},
				{
					value: num(t.claims_waiting),
					label: __("Claims being checked"),
					tone: t.claims_waiting > 0 ? "kc-warn" : "",
					route: "/app/kumar-warranty-claim",
				},
				{
					value: num(t.expiring_45d),
					label: __("Warranties ending soon"),
					tone: t.expiring_45d > 0 ? "kc-warn" : "",
				},
			]
				.map(
					(x) => `
					<${x.route ? "a" : "div"} class="kc-tile ${x.tone || ""}"
						${x.route ? `href="${x.route}"` : ""}>
						<div class="kc-tile-value" title="${x.title || ""}">${x.value}</div>
						<div class="kc-tile-label">${x.label}</div>
					</${x.route ? "a" : "div"}>`
				)
				.join("")
		);

		// ---- actions
		$body.find('[data-act="register"]').on("click", () =>
			frappe.new_doc("Pump Registration")
		);
		$body.find('[data-act="complaint"]').on("click", () =>
			frappe.new_doc("Service Request")
		);
		$body.find('[data-act="lookup"]').on("click", () =>
			frappe.set_route("pump-lookup")
		);
		$body.find('[data-act="claims"]').on("click", () =>
			frappe.set_route("List", "Kumar Warranty Claim")
		);

		// ---- weekly bars, drawn by hand so they stay readable on a phone
		const weeks = d.weekly || [];
		const peak = Math.max(1, ...weeks.map((w) => w.units));
		$body.find("#mb-week").html(
			weeks.length
				? weeks
						.map((w) => {
							const height = Math.max(4, Math.round((w.units / peak) * 78));
							return `
						<div class="kc-week-col">
							<div class="kc-week-n">${w.units}</div>
							<div class="kc-week-bar" style="height:${height}px"></div>
							<div class="kc-week-lbl">${frappe.datetime.str_to_user(w.week_start)}</div>
						</div>`;
						})
						.join("")
				: `<div class="kc-empty">${__("No sales yet in this period.")}</div>`
		);

		// ---- open jobs
		render_list(
			$body.find("#mb-jobs"),
			d.jobs,
			__("Nothing open. All your customers are looked after."),
			(j) => ({
				title: kumar.dash.esc(j.complaint_category || __("Complaint")),
				sub: `${kumar.dash.esc(j.serial_no)} &middot; ${kumar.dash.esc(
					j.customer_name || ""
				)} &middot; ${kumar.dash.date(j.reported_on)}`,
				side: `${kumar.dash.pill(
					j.status,
					j.status === "Open" ? "red" : "orange"
				)}<div style="margin-top:4px;font-size:12px;color:var(--text-muted)">${
					j.is_under_warranty ? __("Free (in warranty)") : __("Chargeable")
				}</div>`,
				go: () => frappe.set_route("Form", "Service Request", j.name),
			})
		);

		// ---- warranties ending, with a tap-to-call
		render_list(
			$body.find("#mb-expiring"),
			d.expiring,
			__("No warranties ending in the next 45 days."),
			(e) => ({
				title: kumar.dash.esc(e.customer || __("Customer")),
				sub: `${kumar.dash.esc(e.model || "")} &middot; ${kumar.dash.esc(
					e.serial_no
				)} &middot; ${__("ends {0}", [kumar.dash.date(e.expires_on)])}`,
				side: e.mobile
					? `<a class="kc-call" href="tel:${kumar.dash.esc(e.mobile)}"
						onclick="event.stopPropagation()">&#9742; ${kumar.dash.esc(e.mobile)}</a>
					   <div style="margin-top:4px;font-size:12px;color:var(--text-muted)">
						${__("{0} days left", [e.days_left])}</div>`
					: `<span class="text-muted">${__("{0} days left", [e.days_left])}</span>`,
				go: () => frappe.set_route("pump-lookup", { sn: e.serial_no }),
			})
		);

		// ---- recent sales
		render_list(
			$body.find("#mb-recent"),
			d.recent,
			__("You have not registered a pump yet. Use the blue button above."),
			(r) => ({
				title: kumar.dash.esc(r.end_customer_name || __("Customer")),
				sub: `${kumar.dash.esc(r.pump_model || "")} &middot; ${kumar.dash.esc(
					r.serial_no
				)} &middot; ${kumar.dash.date(r.sale_date)}`,
				side: `<div style="font-size:12px;color:var(--text-muted)">${kumar.dash.esc(
					r.application_type || ""
				)}</div>
				<div style="font-size:12px;color:var(--text-muted)">${__("warranty to {0}", [
					kumar.dash.date(r.warranty_expiry_date),
				])}</div>`,
				go: () => frappe.set_route("Form", "Pump Registration", r.name),
			})
		);
	}

	// A list, not a table: one row per thing, readable at arm's length.
	function render_list($into, rows, empty_text, shape) {
		if (!rows || !rows.length) {
			$into.html(`<div class="kc-list"><div class="kc-empty">${empty_text}</div></div>`);
			return;
		}
		const items = rows.map(shape);
		$into.html(`
			<div class="kc-list">
				${items
					.map(
						(it, i) => `
					<div class="kc-item" data-i="${i}">
						<div class="kc-item-main">
							<div class="kc-item-title">${it.title}</div>
							<div class="kc-item-sub">${it.sub}</div>
						</div>
						<div class="kc-item-side">${it.side || ""}</div>
					</div>`
					)
					.join("")}
			</div>
		`);
		$into.find(".kc-item").on("click", function () {
			const it = items[$(this).data("i")];
			if (it.go) it.go();
		});
	}

	load();
};
