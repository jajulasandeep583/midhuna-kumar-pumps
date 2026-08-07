// Sales: what was sold, to whom, through whom, and what is still to collect.

frappe.pages["sales-analytics"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Sales Analytics"),
		single_column: true,
	});

	const $main = $(wrapper).find(".layout-main-section");
	const $body = $('<div class="kd-wrap"></div>');
	let latest = null;

	const bar = kumar.dash.date_bar(page, load, "last_30");
	$main.append($body);

	page.set_secondary_action(__("Refresh"), () => {
		const [f, t] = bar.get();
		load(f, t);
	});

	const INVOICE_COLUMNS = [
		{ key: "name", label: __("Invoice"), sort: "text" },
		{ key: "posting_date", label: __("Date"), sort: "text" },
		{ key: "customer_name", label: __("Customer"), sort: "text" },
		{ key: "dealer", label: __("Dealer"), sort: "text" },
		{ key: "amount", label: __("Amount"), align: "right" },
		{ key: "outstanding", label: __("Outstanding"), align: "right" },
		{ key: "status", label: __("Status"), sort: "text" },
	];

	page.add_menu_item(__("Export Invoices (CSV)"), () => {
		if (latest) kumar.dash.csv("kumar-sales.csv", INVOICE_COLUMNS, latest.invoices);
	});
	page.add_menu_item(__("Open Sales Invoice List"), () =>
		frappe.set_route("List", "Sales Invoice")
	);

	function load(from_date, to_date) {
		kumar.dash.load(
			$body,
			"kumar_service.dashboard.sales_analytics",
			{ from_date, to_date },
			render
		);
	}

	function render(d) {
		latest = d;
		const t = d.tiles || {};
		const money = kumar.dash.money;
		const num = kumar.dash.num;

		$body.html(`
			<div id="sa-tiles"></div>

			<div class="kd-grid">
				${kumar.dash.card(__("Revenue by Day"), "sa-revenue", 8)}
				${kumar.dash.card(__("Receivable Ageing"), "sa-ageing", 4)}
			</div>

			<div class="kd-grid">
				${kumar.dash.card(__("Units Sold by Day"), "sa-units", 6)}
				${kumar.dash.card(__("Revenue by Pump Category"), "sa-category", 6)}
			</div>

			<div class="kd-grid">
				${kumar.dash.card(__("Top Dealers"), "sa-dealers", 4)}
				${kumar.dash.card(__("Top Customers"), "sa-customers", 4)}
				${kumar.dash.card(__("Best Selling Models"), "sa-models", 4)}
			</div>

			${kumar.dash.section(
				__("Invoices in this Period"),
				"sa-invoices",
				`<input type="search" class="form-control input-sm sa-search"
					placeholder="${__("Filter by customer or invoice")}" style="width:230px">`
			)}
		`);

		kumar.dash.tiles($body.find("#sa-tiles"), [
			{
				label: __("Revenue"),
				value: money(t.revenue),
				title: kumar.dash.rupees(t.revenue),
				hint: __("{0} invoices", [num(t.invoices)]),
				tone: "good",
				big: true,
			},
			{
				label: __("Net of Tax"),
				value: money(t.net),
				title: kumar.dash.rupees(t.net),
				hint: __("GST {0}", [money(t.tax)]),
			},
			{ label: __("Units Sold"), value: num(t.units), tone: "info" },
			{
				label: __("Average Invoice"),
				value: money(t.avg_invoice),
				title: kumar.dash.rupees(t.avg_invoice),
			},
			{
				label: __("Average Realisation"),
				value: money(t.avg_realisation),
				hint: __("Per pump, net of tax"),
			},
			{
				label: __("Outstanding"),
				value: money(t.outstanding),
				title: kumar.dash.rupees(t.outstanding),
				tone: t.outstanding > 0 ? "warn" : "flat",
			},
		]);

		// ---- revenue trend
		const rev = d.revenue_series || {};
		kumar.dash.chart($body.find("#sa-revenue"), {
			type: "line",
			fill: true,
			labels: rev.labels,
			datasets: [{ name: __("Revenue"), values: rev.values }],
			tooltip: { formatTooltipY: (v) => kumar.dash.rupees(v) },
		});

		// ---- ageing
		const a = d.ageing || {};
		kumar.dash.chart($body.find("#sa-ageing"), {
			type: "bar",
			series: false,
			height: 240,
			labels: [__("Not due"), __("1-30 d"), __("31-60 d"), __("60+ d")],
			datasets: [
				{
					name: __("Outstanding"),
					values: [a.not_due || 0, a.d30 || 0, a.d60 || 0, a.d90 || 0],
				},
			],
			colors: ["#2e9e5b"],
			tooltip: { formatTooltipY: (v) => kumar.dash.rupees(v) },
		});

		// ---- units
		const units = d.units_series || {};
		kumar.dash.chart($body.find("#sa-units"), {
			type: "bar",
			labels: units.labels,
			datasets: [{ name: __("Units"), values: units.values }],
			colors: ["#0b5394"],
		});

		// ---- category mix
		const cat = d.by_category || [];
		kumar.dash.chart($body.find("#sa-category"), {
			type: "donut",
			series: false,
			height: 250,
			labels: cat.map((c) => c.category),
			datasets: [{ name: __("Revenue"), values: cat.map((c) => c.revenue) }],
			tooltip: { formatTooltipY: (v) => kumar.dash.rupees(v) },
		});

		// ---- rankings
		const moneyCol = (key, label) => ({
			key,
			label,
			align: "right",
			format: (v) =>
				`<span class="kd-num" title="${kumar.dash.rupees(v)}">${money(v)}</span>`,
		});

		kumar.dash.table(
			$body.find("#sa-dealers"),
			[
				{ key: "dealer", label: __("Dealer"), sort: "text" },
				{
					key: "units",
					label: __("Units"),
					align: "right",
					format: (v) => `<span class="kd-num">${num(v)}</span>`,
				},
				moneyCol("revenue", __("Revenue")),
			],
			d.top_dealers,
			{
				sort_key: "revenue",
				on_click: (r) =>
					r.dealer &&
					r.dealer !== "(direct)" &&
					frappe.set_route("Form", "Dealer", r.dealer),
			}
		);

		kumar.dash.table(
			$body.find("#sa-customers"),
			[
				{ key: "customer_name", label: __("Customer"), sort: "text" },
				moneyCol("revenue", __("Revenue")),
				moneyCol("outstanding", __("Due")),
			],
			d.top_customers,
			{
				sort_key: "revenue",
				on_click: (r) => frappe.set_route("Form", "Customer", r.customer),
			}
		);

		kumar.dash.table(
			$body.find("#sa-models"),
			[
				{ key: "model", label: __("Model"), sort: "text" },
				{
					key: "qty",
					label: __("Units"),
					align: "right",
					format: (v) => `<span class="kd-num">${num(v)}</span>`,
				},
				moneyCol("revenue", __("Revenue")),
			],
			d.top_models,
			{ sort_key: "revenue" }
		);

		// ---- invoice table
		const columns = [
			{
				key: "name",
				label: __("Invoice"),
				sort: "text",
				format: (v) => `<b>${kumar.dash.esc(v)}</b>`,
			},
			{
				key: "posting_date",
				label: __("Date"),
				sort: "text",
				format: (v) => kumar.dash.date(v),
			},
			{ key: "customer_name", label: __("Customer"), sort: "text" },
			{
				key: "dealer",
				label: __("Dealer"),
				sort: "text",
				format: (v) => kumar.dash.esc(v || "-"),
			},
			moneyCol("amount", __("Amount")),
			{
				key: "outstanding",
				label: __("Outstanding"),
				align: "right",
				format: (v) =>
					v > 0
						? `<span class="kd-num" style="color:#c2354a" title="${kumar.dash.rupees(
								v
						  )}">${money(v)}</span>`
						: `<span class="text-muted">${__("Paid")}</span>`,
			},
			{
				key: "status",
				label: __("Status"),
				sort: "text",
				format: (v) => kumar.dash.pill(v, kumar.dash.status_colour(v)),
			},
		];

		const draw = (rows) =>
			kumar.dash.table($body.find("#sa-invoices"), columns, rows, {
				sort_key: "posting_date",
				sort_dir: "desc",
				empty: __("No invoices match."),
				on_click: (r) => frappe.set_route("Form", "Sales Invoice", r.name),
			});

		draw(d.invoices);

		$body.find(".sa-search").on("input", function () {
			const q = ($(this).val() || "").toLowerCase();
			draw(
				(d.invoices || []).filter(
					(r) =>
						!q ||
						String(r.customer_name || "").toLowerCase().includes(q) ||
						String(r.name || "").toLowerCase().includes(q) ||
						String(r.dealer || "").toLowerCase().includes(q)
				)
			);
		});
	}

	const [f0, t0] = bar.get();
	load(f0, t0);
};
