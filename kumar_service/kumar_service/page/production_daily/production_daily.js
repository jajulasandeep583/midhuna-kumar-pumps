// The shop-floor board: what came off the line each day, on whose shift, and
// whether it passed test.
//
// Output and quality are shown on the same chart on purpose. Units produced
// on its own is a number a plant can always make go up; units produced next
// to pass rate is the number that means something.

frappe.pages["production-daily"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Daily Production"),
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

	page.add_menu_item(__("Export Work Orders (CSV)"), () => {
		if (!latest) return;
		kumar.dash.csv(
			"kumar-work-orders.csv",
			[
				{ key: "name", label: __("Work Order") },
				{ key: "model", label: __("Model") },
				{ key: "qty", label: __("Planned") },
				{ key: "produced_qty", label: __("Produced") },
				{ key: "status", label: __("Status") },
				{ key: "shift", label: __("Shift") },
				{ key: "heat_no", label: __("Heat") },
				{ key: "winding_batch", label: __("Winding Batch") },
			],
			latest.work_orders
		);
	});
	page.add_menu_item(__("Open Work Order List"), () =>
		frappe.set_route("List", "Work Order")
	);
	page.add_menu_item(__("Pump Lookup"), () => frappe.set_route("pump-lookup"));

	function load(from_date, to_date) {
		kumar.dash.load(
			$body,
			"kumar_service.dashboard.production_daily",
			{ from_date, to_date },
			render
		);
	}

	function render(d) {
		latest = d;
		const t = d.tiles || {};
		const num = kumar.dash.num;

		$body.html(`
			<div id="pd-tiles"></div>

			<div class="kd-grid">
				${kumar.dash.card(__("Built and Tested, by Day"), "pd-output", 8)}
				${kumar.dash.card(__("Output by Shift"), "pd-shift", 4)}
			</div>

			<div class="kd-grid">
				${kumar.dash.card(__("Foundry Heats by Day"), "pd-heat", 6)}
				${kumar.dash.card(__("Stators Wound by Day"), "pd-winding", 6)}
			</div>

			<div class="kd-grid">
				${kumar.dash.card(__("Models Built"), "pd-models", 6)}
				${kumar.dash.card(__("Work Order Status"), "pd-status", 6)}
			</div>

			${kumar.dash.section(
				__("Work Orders in this Period"),
				"pd-orders",
				`<input type="search" class="form-control input-sm pd-search"
					placeholder="${__("Filter by model, heat or shift")}" style="width:240px">`
			)}
		`);

		kumar.dash.tiles($body.find("#pd-tiles"), [
			{
				label: __("Units Produced"),
				value: num(t.units_produced),
				hint: __("{0} a day on average", [t.daily_average]),
				tone: "good",
				big: true,
			},
			{
				label: __("Test Pass Rate"),
				value: kumar.dash.pct(t.test_pass_pct),
				hint: __("{0} units tested", [num(t.tested)]),
				tone: t.test_pass_pct >= 95 ? "good" : "bad",
			},
			{
				label: __("Work Orders"),
				value: num(t.work_orders),
				hint: __("{0} completed, {1} on the floor", [
					num(t.wo_completed),
					num(t.wo_in_process),
				]),
				tone: "info",
			},
			{
				label: __("Foundry Heats"),
				value: num(t.heats),
				hint: __("{0} kg charged", [num(t.charge_kg)]),
			},
			{
				label: __("Winding Rejects"),
				value: kumar.dash.pct(t.winding_reject_pct),
				hint: __("{0} stators wound", [num(t.winding_produced)]),
				tone: t.winding_reject_pct > 4 ? "bad" : "good",
			},
			{
				label: __("Dispatched"),
				value: num(t.dispatched),
				hint: __("Units delivered in this period"),
			},
			{
				label: __("Finished Stock"),
				value: num(t.fg_stock),
				hint: __("Pumps on hand right now"),
				tone: "flat",
			},
		]);

		// ---- output vs tested vs passed
		const prod = d.produced_series || {};
		const tested = d.tested_series || {};
		const passed = d.passed_series || {};
		kumar.dash.chart($body.find("#pd-output"), {
			type: "axis-mixed",
			labels: prod.labels,
			datasets: [
				{ name: __("Built"), values: prod.values, chartType: "bar" },
				{ name: __("Tested"), values: tested.values, chartType: "line" },
				{ name: __("Passed"), values: passed.values, chartType: "line" },
			],
			colors: ["#0b5394", "#e0781a", "#2e9e5b"],
		});

		// ---- shifts
		const shifts = d.by_shift || [];
		kumar.dash.chart($body.find("#pd-shift"), {
			type: "bar",
			series: false,
			height: 240,
			labels: shifts.map((s) => __("Shift {0}", [s.shift])),
			datasets: [{ name: __("Units"), values: shifts.map((s) => s.units) }],
			colors: ["#8b3fa8"],
		});

		// ---- foundry
		const heat = d.heat_series || {};
		kumar.dash.chart($body.find("#pd-heat"), {
			type: "bar",
			labels: heat.labels,
			datasets: [{ name: __("Heats"), values: heat.values }],
			colors: ["#c2354a"],
		});

		// ---- winding
		const wind = d.winding_series || {};
		kumar.dash.chart($body.find("#pd-winding"), {
			type: "line",
			fill: true,
			labels: wind.labels,
			datasets: [{ name: __("Stators"), values: wind.values }],
			colors: ["#0f8b9e"],
		});

		// ---- models built
		kumar.dash.table(
			$body.find("#pd-models"),
			[
				{ key: "model", label: __("Model"), sort: "text" },
				{
					key: "units",
					label: __("Units Built"),
					align: "right",
					format: (v) => `<span class="kd-num">${num(v)}</span>`,
				},
			],
			d.by_model,
			{ sort_key: "units", empty: __("Nothing was built in this period.") }
		);

		// ---- work order status
		kumar.dash.table(
			$body.find("#pd-status"),
			[
				{
					key: "status",
					label: __("Status"),
					sort: "text",
					format: (v) => kumar.dash.pill(v, kumar.dash.status_colour(v)),
				},
				{
					key: "n",
					label: __("Orders"),
					align: "right",
					format: (v) => `<span class="kd-num">${num(v)}</span>`,
				},
				{
					key: "planned",
					label: __("Planned"),
					align: "right",
					format: (v) => `<span class="kd-num">${num(v)}</span>`,
				},
				{
					key: "produced",
					label: __("Produced"),
					align: "right",
					format: (v) => `<span class="kd-num">${num(v)}</span>`,
				},
			],
			d.wo_status,
			{ sort_key: "n" }
		);

		// ---- the order board
		const columns = [
			{
				key: "name",
				label: __("Work Order"),
				sort: "text",
				format: (v) => `<b>${kumar.dash.esc(v)}</b>`,
			},
			{
				key: "planned_start_date",
				label: __("Start"),
				sort: "text",
				format: (v) => kumar.dash.date(v),
			},
			{
				key: "model",
				label: __("Model"),
				sort: "text",
				format: (v, r) => kumar.dash.esc(v || r.production_item),
			},
			{
				key: "qty",
				label: __("Planned"),
				align: "right",
				format: (v) => `<span class="kd-num">${num(v)}</span>`,
			},
			{
				key: "produced_qty",
				label: __("Produced"),
				align: "right",
				format: (v, r) => {
					const pct = r.qty ? (Number(v) / Number(r.qty)) * 100 : 0;
					return `
						<div style="display:flex;align-items:center;gap:8px;justify-content:flex-end">
							<div class="kd-bar-mini"><span style="width:${Math.min(100, pct)}%"></span></div>
							<span class="kd-num">${num(v)}</span>
						</div>`;
				},
			},
			{
				key: "shift",
				label: __("Shift"),
				sort: "text",
				format: (v) => kumar.dash.esc(v || "-"),
			},
			{
				key: "heat_no",
				label: __("Heat"),
				sort: "text",
				format: (v) => kumar.dash.esc(v || "-"),
			},
			{
				key: "winding_batch",
				label: __("Winding"),
				sort: "text",
				format: (v) => kumar.dash.esc(v || "-"),
			},
			{
				key: "status",
				label: __("Status"),
				sort: "text",
				format: (v) => kumar.dash.pill(v, kumar.dash.status_colour(v)),
			},
		];

		const draw = (rows) =>
			kumar.dash.table($body.find("#pd-orders"), columns, rows, {
				sort_key: "planned_start_date",
				empty: __("No work orders match."),
				on_click: (r) => frappe.set_route("Form", "Work Order", r.name),
			});

		draw(d.work_orders);

		$body.find(".pd-search").on("input", function () {
			const q = ($(this).val() || "").toLowerCase();
			draw(
				(d.work_orders || []).filter(
					(r) =>
						!q ||
						String(r.model || "").toLowerCase().includes(q) ||
						String(r.heat_no || "").toLowerCase().includes(q) ||
						String(r.shift || "").toLowerCase().includes(q) ||
						String(r.name || "").toLowerCase().includes(q)
				)
			);
		});
	}

	const [f0, t0] = bar.get();
	load(f0, t0);
};
