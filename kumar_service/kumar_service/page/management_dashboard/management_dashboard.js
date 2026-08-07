// The screen the proprietor opens first: is the month working?
//
// Deliberately shallow. It answers "how are we doing" and then hands off to
// the screen that answers "why" - sales, purchase, production, people. Every
// tile and every chart is a door to one of those.

frappe.pages["management-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Management Dashboard"),
		single_column: true,
	});

	const $main = $(wrapper).find(".layout-main-section");
	const $body = $('<div class="kd-wrap"></div>');

	const bar = kumar.dash.date_bar(page, load, "last_30");
	$main.append($body);

	page.set_secondary_action(__("Refresh"), () => {
		const [f, t] = bar.get();
		load(f, t);
	});

	page.add_menu_item(__("Sales"), () => frappe.set_route("sales-analytics"));
	page.add_menu_item(__("Purchase"), () => frappe.set_route("purchase-analytics"));
	page.add_menu_item(__("Production"), () => frappe.set_route("production-daily"));
	page.add_menu_item(__("Dealer Network"), () => frappe.set_route("dealer-network"));
	page.add_menu_item(__("People & Payroll"), () => frappe.set_route("people-payroll"));

	function load(from_date, to_date) {
		kumar.dash.load(
			$body,
			"kumar_service.dashboard.management_overview",
			{ from_date, to_date },
			render
		);
	}

	function render(d) {
		const t = d.tiles || {};
		const money = kumar.dash.money;
		const num = kumar.dash.num;

		$body.html(`
			<div id="md-tiles"></div>

			<div class="kd-grid">
				${kumar.dash.card(__("Revenue by Day"), "md-revenue", 7)}
				${kumar.dash.card(__("Order to Invoice"), "md-pipeline", 5)}
			</div>

			<div class="kd-grid">
				${kumar.dash.card(__("Units Produced by Day"), "md-production", 7)}
				${kumar.dash.card(__("Best Selling Models"), "md-models", 5)}
			</div>

			<div class="kd-grid">
				${kumar.dash.card(__("Go To"), "md-links", 12)}
			</div>
		`);

		// ---- tiles: money first, then the plant, then the people
		kumar.dash.tiles($body.find("#md-tiles"), [
			{
				label: __("Revenue"),
				value: money(t.revenue),
				title: kumar.dash.rupees(t.revenue),
				hint: __("{0} invoices", [num(t.invoices)]),
				tone: "good",
				big: true,
				href: "/app/sales-analytics",
			},
			{
				label: __("Purchase Spend"),
				value: money(t.purchase_spend),
				title: kumar.dash.rupees(t.purchase_spend),
				hint: __("Payable {0}", [money(t.payable)]),
				tone: "warn",
				href: "/app/purchase-analytics",
			},
			{
				label: __("Gross Margin"),
				value: kumar.dash.pct(t.gross_margin_pct),
				title: kumar.dash.rupees(t.gross_profit),
				hint: __("Net sales less cost of goods sold ({0})", [money(t.cogs)]),
				tone: t.gross_margin_pct >= 0 ? "good" : "bad",
			},
			{
				label: __("Receivable"),
				value: money(t.receivable),
				title: kumar.dash.rupees(t.receivable),
				hint: __("Money still to collect"),
				tone: t.receivable > 0 ? "warn" : "flat",
			},
			{
				label: __("Units Produced"),
				value: num(t.units_produced),
				hint: __("{0} production runs", [num(t.production_runs)]),
				tone: "info",
				href: "/app/production-daily",
			},
			{
				label: __("Test Pass Rate"),
				value: kumar.dash.pct(t.test_pass_pct),
				hint: __("{0} units tested", [num(t.tested)]),
				tone: t.test_pass_pct >= 95 ? "good" : "bad",
			},
			{
				label: __("Pumps Registered"),
				value: num(t.units_registered),
				hint: __("Warranty started"),
				href: "/app/pump-registration",
			},
			{
				label: __("Open Complaints"),
				value: num(t.complaints_open),
				hint: __("{0} raised this period", [num(t.complaints)]),
				tone: t.complaints_open > 0 ? "bad" : "good",
				href: "/app/service-request",
			},
			{
				label: __("Warranty Claims"),
				value: num(t.claims),
				hint: __("Raised this period"),
				href: "/app/kumar-warranty-claim",
			},
			{
				label: __("Headcount"),
				value: num(t.headcount),
				hint: __("Wage bill {0}", [money(t.wage_bill)]),
				tone: "info",
				href: "/app/people-payroll",
			},
		]);

		// ---- revenue
		const rev = d.revenue_series || {};
		kumar.dash.chart($body.find("#md-revenue"), {
			type: "line",
			fill: true,
			labels: rev.labels,
			datasets: [{ name: __("Revenue"), values: rev.values }],
			tooltip: { formatTooltipY: (v) => kumar.dash.rupees(v) },
		});

		// ---- pipeline: order -> delivered -> invoiced, as a funnel
		const p = d.pipeline || {};
		kumar.dash.chart($body.find("#md-pipeline"), {
			type: "bar",
			series: false,
			height: 240,
			labels: [__("Ordered"), __("Delivered"), __("Invoiced")],
			datasets: [
				{
					name: __("Value"),
					values: [
						(p.orders || {}).value || 0,
						(p.delivered || {}).value || 0,
						(p.invoiced || {}).value || 0,
					],
				},
			],
			tooltip: { formatTooltipY: (v) => kumar.dash.rupees(v) },
		});
		$body.find("#md-pipeline").append(`
			<div class="kd-tile-hint" style="margin-top:8px">
				${__("{0} orders, {1} deliveries, {2} invoices in this period", [
					kumar.dash.num((p.orders || {}).count),
					kumar.dash.num((p.delivered || {}).count),
					kumar.dash.num((p.invoiced || {}).count),
				])}
			</div>`);

		// ---- production
		const prod = d.production_series || {};
		kumar.dash.chart($body.find("#md-production"), {
			type: "bar",
			labels: prod.labels,
			datasets: [{ name: __("Units"), values: prod.values }],
			colors: ["#2e9e5b"],
		});

		// ---- top models
		kumar.dash.table(
			$body.find("#md-models"),
			[
				{ key: "model", label: __("Model"), sort: "text" },
				{
					key: "qty",
					label: __("Units"),
					align: "right",
					format: (v) => `<span class="kd-num">${kumar.dash.num(v)}</span>`,
				},
				{
					key: "revenue",
					label: __("Revenue"),
					align: "right",
					format: (v) =>
						`<span class="kd-num" title="${kumar.dash.rupees(v)}">${kumar.dash.money(
							v
						)}</span>`,
				},
			],
			d.top_models,
			{
				sort_key: "revenue",
				empty: __("No sales in this period."),
				on_click: (row) =>
					row.model && frappe.set_route("Form", "Pump Model", row.model),
			}
		);

		// ---- the doors out of this screen
		$body.find("#md-links").html(`
			<div class="kd-tiles">
				${[
					["sales-analytics", __("Sales"), __("Revenue, customers, ageing")],
					["purchase-analytics", __("Purchase"), __("Spend, suppliers, pending")],
					["production-daily", __("Production"), __("Daily output, shifts, quality")],
					["dealer-network", __("Dealer Network"), __("Distribution and performance")],
					["people-payroll", __("People"), __("Headcount, attendance, wages")],
					["pump-lookup", __("Pump Lookup"), __("Trace one serial")],
				]
					.map(
						([route, label, hint]) => `
					<a class="kd-tile kd-link kd-flat" href="/app/${route}">
						<div class="kd-tile-value" style="font-size:16px">${label}</div>
						<div class="kd-tile-hint">${hint}</div>
					</a>`
					)
					.join("")}
			</div>
		`);
	}

	const [f0, t0] = bar.get();
	load(f0, t0);
};
