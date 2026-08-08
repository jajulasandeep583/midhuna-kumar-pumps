// Service & Warranty Command Centre.
//
// The service desk and the warranty desk exist to answer customers and dealers,
// so the headline here is not revenue - it is HOW MANY WE CLOSED. Everything
// below the tiles explains that number: what is still open, who is late, which
// service centre is carrying the load, which model keeps coming back, and what
// the warranty is costing.
//
// Raised and Resolved are counted separately and never added together. A
// complaint raised in June and closed in July belongs to June's intake and
// July's output; rolling them into one figure is how a service desk convinces
// itself it is keeping up when it is not.

frappe.pages["service-command-centre"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Service & Warranty Command Centre"),
		single_column: true,
	});

	const $main = $(wrapper).find(".layout-main-section");
	const $body = $('<div class="kd-wrap"></div>');
	let latest = null;

	const bar = kumar.dash.date_bar(page, load, "last_30");
	$main.append($body);

	const dealer_field = page.add_field({
		fieldname: "dealer",
		label: __("Dealer"),
		fieldtype: "Link",
		options: "Dealer",
		change() {
			const [f, t] = bar.get();
			load(f, t);
		},
	});

	page.set_secondary_action(__("Refresh"), () => {
		const [f, t] = bar.get();
		load(f, t);
	});

	page.add_menu_item(__("Dealer Conversations"), () =>
		frappe.set_route("dealer-conversations"));
	page.add_menu_item(__("Dealer Requests & Claims report"), () =>
		frappe.set_route("query-report", "Dealer Requests & Claims"));
	page.add_menu_item(__("Export Open Tickets (CSV)"), () => {
		if (!latest) return;
		kumar.dash.csv("kumar-open-tickets.csv", OLDEST_COLUMNS, latest.oldest_open);
	});

	// ------------------------------------------------------------- columns
	const num = (v) => kumar.dash.num(v);
	const pct = (v) => `${flt(v, 1)}%`;

	const CENTRE_COLUMNS = [
		{ key: "centre", label: __("Service Centre") },
		{ key: "raised", label: __("Raised"), align: "right", format: num },
		{ key: "resolved", label: __("Resolved"), align: "right", format: num },
		{ key: "close_pct", label: __("Closed %"), align: "right", format: pct },
		{ key: "open_now", label: __("Open Now"), align: "right", format: num },
		{ key: "late", label: __("Late"), align: "right", format: num },
		{ key: "avg_days", label: __("Avg Days"), align: "right" },
		{ key: "sla_pct", label: __("SLA Met %"), align: "right", format: pct },
	];

	const DEALER_COLUMNS = [
		{ key: "dealer", label: __("Dealer") },
		{ key: "raised", label: __("Complaints"), align: "right", format: num },
		{ key: "resolved", label: __("Resolved"), align: "right", format: num },
		{ key: "close_pct", label: __("Closed %"), align: "right", format: pct },
		{ key: "open_now", label: __("Open Now"), align: "right", format: num },
		{ key: "in_warranty", label: __("Free (in warranty)"), align: "right", format: num },
	];

	const TECH_COLUMNS = [
		{ key: "technician", label: __("Technician") },
		{ key: "raised", label: __("Tickets Assigned"), align: "right", format: num },
		{ key: "resolved", label: __("Resolved"), align: "right", format: num },
		{ key: "close_pct", label: __("Closed %"), align: "right", format: pct },
		{ key: "avg_days", label: __("Avg Days"), align: "right" },
	];

	const CATEGORY_COLUMNS = [
		{ key: "label", label: __("Complaint") },
		{ key: "raised", label: __("Raised"), align: "right", format: num },
		{ key: "resolved", label: __("Resolved"), align: "right", format: num },
		{ key: "in_warranty", label: __("In warranty"), align: "right", format: num },
	];

	const MODEL_COLUMNS = [
		{ key: "model", label: __("Model") },
		{ key: "complaints", label: __("Complaints"), align: "right", format: num },
		{ key: "defects", label: __("Manufacturing Defect"), align: "right", format: num },
	];

	const OLDEST_COLUMNS = [
		{ key: "name", label: __("Request") },
		{ key: "age_days", label: __("Days Open"), align: "right", format: num },
		{ key: "dealer", label: __("Dealer") },
		{ key: "complaint_category", label: __("Complaint"), format: (v) => __(v || "") },
		{ key: "serial_no", label: __("Serial No") },
		{ key: "end_customer_name", label: __("Customer") },
		{ key: "end_customer_mobile", label: __("Mobile") },
		{ key: "assigned_technician", label: __("Technician") },
		{
			key: "answered",
			label: __("Answered"),
			align: "center",
			format: (v) =>
				v
					? `<span class="kd-pill kd-good">${__("Yes")}</span>`
					: `<span class="kd-pill kd-bad">${__("No")}</span>`,
		},
		{
			key: "late",
			label: __("Late"),
			align: "center",
			format: (v) => (v ? `<span class="kd-pill kd-bad">${__("Late")}</span>` : ""),
		},
	];

	// ---------------------------------------------------------------- load
	function load(from_date, to_date) {
		if (!from_date) {
			const [f, t] = bar.get();
			from_date = f;
			to_date = t;
		}
		$body.html(`<div class="kd-loading">${__("Loading...")}</div>`);
		frappe.call({
			method: "kumar_service.dashboard.service_command_centre",
			args: { from_date, to_date, dealer: dealer_field.get_value() || null },
			callback(r) {
				latest = r.message;
				render(latest);
			},
			error() {
				$body.html(
					`<div class="kd-empty">${__("Could not load this screen. You may not have permission for it.")}</div>`
				);
			},
		});
	}

	// -------------------------------------------------------------- render
	function render(d) {
		if (!d) return;
		const t = d.tiles;

		$body.html(`
			<div id="cc-tiles"></div>
			${kumar.dash.section(__("Raised and Resolved, by Day"), "cc-flow")}
			<div class="kd-grid">
				${kumar.dash.card(__("What Customers Complain About"), "cc-category", 6)}
				${kumar.dash.card(__("Root Cause of What We Closed"), "cc-cause", 6)}
			</div>
			${kumar.dash.section(__("Service Centre Load"), "cc-centre")}
			<div class="kd-grid">
				${kumar.dash.card(__("Warranty Claims by Stage"), "cc-claims", 6)}
				${kumar.dash.card(__("Models That Keep Coming Back"), "cc-model", 6)}
			</div>
			<div class="kd-grid">
				${kumar.dash.card(__("Complaints by Dealer"), "cc-dealer", 6)}
				${kumar.dash.card(__("Technician Workload"), "cc-tech", 6)}
			</div>
			${kumar.dash.section(__("Oldest Still Open"), "cc-oldest")}
		`);

		const arrow = (g) =>
			g === null || g === undefined
				? __("new")
				: `${g >= 0 ? "&#9650;" : "&#9660;"} ${Math.abs(flt(g, 1))}%`;

		kumar.dash.tiles($body.find("#cc-tiles"), [
			{
				label: __("Queries We Closed"),
				value: num(t.resolved),
				hint: arrow(t.resolved_growth) + " " + __("vs the period before"),
				tone: "good",
				big: true,
			},
			{
				label: __("Queries That Came In"),
				value: num(t.raised),
				hint: __("{0} a day on average", [flt(t.per_day, 1)]),
			},
			{
				label: __("Closed vs Raised"),
				value: pct(t.close_rate),
				hint:
					t.close_rate >= 100
						? __("Eating into the backlog")
						: __("Below 100% means the backlog grew"),
				tone: t.close_rate >= 95 ? "good" : t.close_rate >= 75 ? "warn" : "bad",
			},
			{
				label: __("Open Right Now"),
				value: num(t.open_now),
				hint: __("{0} past the promised date", [num(t.late_now)]),
				tone: t.late_now ? "bad" : "good",
			},
			{
				label: __("No Reply Yet"),
				value: num(t.unanswered),
				hint: __("Nobody has answered these"),
				tone: t.unanswered ? "bad" : "good",
			},
			{
				label: __("SLA Met"),
				value: pct(t.sla_pct),
				hint: __("Responded or closed inside the promise"),
				tone: t.sla_pct >= 85 ? "good" : t.sla_pct >= 70 ? "warn" : "bad",
			},
			{
				label: __("Average Days to Close"),
				value: flt(t.avg_days, 1),
				hint: __("From the customer's call to resolution"),
			},
			{
				label: __("Free Visits"),
				value: num(t.free_visits),
				hint: __("Covered by warranty, no charge to the customer"),
			},
			{
				label: __("Repeat Failures"),
				value: num(t.repeat_failures),
				hint: __("Same pump reported more than once"),
				tone: t.repeat_failures ? "warn" : "good",
			},
			{
				label: __("Warranty Claims In"),
				value: num(t.claims_raised),
				hint: __("{0} settled, {1} still open", [num(t.claims_settled), num(t.claims_open)]),
			},
			{
				label: __("Claim Value"),
				value: kumar.dash.money(t.claim_value),
				hint: __("Approved {0}", [kumar.dash.money(t.claim_approved)]),
				title: t.claim_value,
			},
		]);

		// The one chart that matters: is the line coming in above or below the
		// line going out.
		kumar.dash.chart($body.find("#cc-flow"), {
			type: "line",
			labels: d.raised_series.labels,
			datasets: [
				{ name: __("Raised"), values: d.raised_series.values },
				{ name: __("Resolved"), values: d.resolved_series.values },
			],
			colors: ["#c2354a", "#2e9e5b"],
			height: 250,
		});

		kumar.dash.table($body.find("#cc-category"), CATEGORY_COLUMNS, d.by_category, {
			sort_key: "raised",
			limit: 10,
		});

		kumar.dash.chart($body.find("#cc-cause"), {
			type: "bar",
			series: false,
			labels: (d.by_root_cause || []).map((r) => __(r.label)),
			datasets: [{ name: __("Closed"), values: (d.by_root_cause || []).map((r) => r.total) }],
			height: 240,
		});

		kumar.dash.table($body.find("#cc-centre"), CENTRE_COLUMNS, d.by_centre, {
			sort_key: "raised",
			empty: __("No complaints in this period."),
		});

		kumar.dash.chart($body.find("#cc-claims"), {
			type: "donut",
			series: false,
			labels: (d.claim_states || []).map((r) => __(r.state)),
			datasets: [{ name: __("Claims"), values: (d.claim_states || []).map((r) => r.n) }],
			height: 240,
		});

		kumar.dash.table($body.find("#cc-model"), MODEL_COLUMNS, d.by_model, {
			sort_key: "complaints",
			on_click: (row) =>
				row.model && frappe.set_route("Form", "Pump Model", row.model),
		});

		kumar.dash.table($body.find("#cc-dealer"), DEALER_COLUMNS, d.by_dealer, {
			sort_key: "raised",
			on_click: (row) => row.dealer && frappe.set_route("Form", "Dealer", row.dealer),
		});

		kumar.dash.table($body.find("#cc-tech"), TECH_COLUMNS, d.by_technician, {
			sort_key: "raised",
		});

		kumar.dash.table($body.find("#cc-oldest"), OLDEST_COLUMNS, d.oldest_open, {
			sort_key: "age_days",
			empty: __("Nothing is open. Every query has been closed."),
			on_click: (row) => frappe.set_route("Form", "Service Request", row.name),
		});
	}

	load();
};
