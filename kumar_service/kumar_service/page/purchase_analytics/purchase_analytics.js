// Purchase: what the plant is buying, from whom, and what is stuck.
//
// The pipeline tiles matter more than the spend chart here - an order that
// was raised and never received is money committed and material missing, and
// that is the thing a purchase manager needs to see first.

frappe.pages["purchase-analytics"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Purchase Analytics"),
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
		{ key: "name", label: __("Invoice") },
		{ key: "posting_date", label: __("Date") },
		{ key: "supplier", label: __("Supplier") },
		{ key: "bill_no", label: __("Bill No") },
		{ key: "amount", label: __("Amount") },
		{ key: "outstanding", label: __("Outstanding") },
		{ key: "status", label: __("Status") },
	];

	page.add_menu_item(__("Export Invoices (CSV)"), () => {
		if (latest) kumar.dash.csv("kumar-purchase.csv", INVOICE_COLUMNS, latest.invoices);
	});
	page.add_menu_item(__("Open Purchase Order List"), () =>
		frappe.set_route("List", "Purchase Order")
	);

	function load(from_date, to_date) {
		kumar.dash.load(
			$body,
			"kumar_service.dashboard.purchase_analytics",
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
			<div id="pa-tiles"></div>

			<div class="kd-grid">
				${kumar.dash.card(__("Spend by Day"), "pa-spend", 8)}
				${kumar.dash.card(__("Payable Ageing"), "pa-ageing", 4)}
			</div>

			<div class="kd-grid">
				${kumar.dash.card(__("Top Suppliers"), "pa-suppliers", 6)}
				${kumar.dash.card(__("Spend by Material Type"), "pa-group", 6)}
			</div>

			${kumar.dash.section(__("What We Bought"), "pa-items")}
			${kumar.dash.section(__("Orders Still Open"), "pa-orders")}
			${kumar.dash.section(
				__("Supplier Invoices"),
				"pa-invoices",
				`<input type="search" class="form-control input-sm pa-search"
					placeholder="${__("Filter by supplier or bill")}" style="width:230px">`
			)}
		`);

		kumar.dash.tiles($body.find("#pa-tiles"), [
			{
				label: __("Purchase Spend"),
				value: money(t.spend),
				title: kumar.dash.rupees(t.spend),
				hint: __("{0} invoices", [num(t.invoices)]),
				tone: "warn",
				big: true,
			},
			{
				label: __("Net of Tax"),
				value: money(t.net),
				title: kumar.dash.rupees(t.net),
				hint: __("Input GST {0}", [money(t.tax)]),
			},
			{
				label: __("Payable"),
				value: money(t.outstanding),
				title: kumar.dash.rupees(t.outstanding),
				hint: __("Still to pay suppliers"),
				tone: t.outstanding > 0 ? "bad" : "flat",
			},
			{
				label: __("Orders Placed"),
				value: num(t.orders),
				hint: money(t.order_value),
				tone: "info",
			},
			{
				label: __("Awaiting Delivery"),
				value: num(t.pending_receipt),
				hint: __("Ordered, not received"),
				tone: t.pending_receipt > 0 ? "warn" : "good",
			},
			{
				label: __("Awaiting Bill"),
				value: num(t.pending_bill),
				hint: __("Received, not invoiced"),
				tone: t.pending_bill > 0 ? "warn" : "good",
			},
			{
				label: __("Goods Received"),
				value: num(t.receipts),
				hint: money(t.receipt_value),
			},
			{
				label: __("Open Requisitions"),
				value: num(t.requests_open),
				hint: __("{0} raised in this period", [num(t.requests)]),
			},
			{ label: __("Suppliers"), value: num(t.suppliers), tone: "flat" },
		]);

		// ---- spend
		const spend = d.spend_series || {};
		kumar.dash.chart($body.find("#pa-spend"), {
			type: "bar",
			labels: spend.labels,
			datasets: [{ name: __("Spend"), values: spend.values }],
			colors: ["#e0781a"],
			tooltip: { formatTooltipY: (v) => kumar.dash.rupees(v) },
		});

		// ---- ageing
		const a = d.ageing || {};
		kumar.dash.chart($body.find("#pa-ageing"), {
			type: "bar",
			series: false,
			height: 240,
			labels: [__("Not due"), __("1-30 d"), __("31-60 d"), __("60+ d")],
			datasets: [
				{
					name: __("Payable"),
					values: [a.not_due || 0, a.d30 || 0, a.d60 || 0, a.d90 || 0],
				},
			],
			colors: ["#c2354a"],
			tooltip: { formatTooltipY: (v) => kumar.dash.rupees(v) },
		});

		const moneyCol = (key, label) => ({
			key,
			label,
			align: "right",
			format: (v) =>
				`<span class="kd-num" title="${kumar.dash.rupees(v)}">${money(v)}</span>`,
		});

		// ---- suppliers
		kumar.dash.table(
			$body.find("#pa-suppliers"),
			[
				{ key: "supplier_name", label: __("Supplier"), sort: "text" },
				{
					key: "invoices",
					label: __("Bills"),
					align: "right",
					format: (v) => `<span class="kd-num">${num(v)}</span>`,
				},
				moneyCol("spend", __("Spend")),
				moneyCol("outstanding", __("Payable")),
			],
			d.top_suppliers,
			{
				sort_key: "spend",
				on_click: (r) => frappe.set_route("Form", "Supplier", r.supplier),
			}
		);

		// ---- material mix
		const groups = d.by_group || [];
		kumar.dash.chart($body.find("#pa-group"), {
			type: "donut",
			series: false,
			height: 250,
			labels: groups.map((g) => g.item_group),
			datasets: [{ name: __("Spend"), values: groups.map((g) => g.value) }],
			tooltip: { formatTooltipY: (v) => kumar.dash.rupees(v) },
		});

		// ---- items
		kumar.dash.table(
			$body.find("#pa-items"),
			[
				{ key: "item_name", label: __("Material"), sort: "text" },
				{ key: "item_group", label: __("Type"), sort: "text" },
				{
					key: "qty",
					label: __("Quantity"),
					align: "right",
					format: (v, r) => `<span class="kd-num">${num(v)}</span> ${
						kumar.dash.esc(r.uom || "")
					}`,
				},
				{
					key: "avg_rate",
					label: __("Avg Rate"),
					align: "right",
					format: (v) => `<span class="kd-num">${kumar.dash.rupees(v)}</span>`,
				},
				moneyCol("value", __("Value")),
			],
			d.top_items,
			{
				sort_key: "value",
				empty: __("Nothing purchased in this period."),
				on_click: (r) => frappe.set_route("Form", "Item", r.item_code),
			}
		);

		// ---- open orders, with a progress bar for how much has landed
		kumar.dash.table(
			$body.find("#pa-orders"),
			[
				{
					key: "name",
					label: __("Order"),
					sort: "text",
					format: (v) => `<b>${kumar.dash.esc(v)}</b>`,
				},
				{
					key: "transaction_date",
					label: __("Date"),
					sort: "text",
					format: (v) => kumar.dash.date(v),
				},
				{ key: "supplier", label: __("Supplier"), sort: "text" },
				moneyCol("amount", __("Value")),
				{
					key: "per_received",
					label: __("Received"),
					align: "right",
					format: (v) => `
						<div style="display:flex;align-items:center;gap:8px;justify-content:flex-end">
							<div class="kd-bar-mini"><span style="width:${Math.min(
								100,
								Number(v || 0)
							)}%"></span></div>
							<span class="kd-num">${Math.round(Number(v || 0))}%</span>
						</div>`,
				},
				{
					key: "per_billed",
					label: __("Billed"),
					align: "right",
					format: (v) => `<span class="kd-num">${Math.round(Number(v || 0))}%</span>`,
				},
				{
					key: "status",
					label: __("Status"),
					sort: "text",
					format: (v) => kumar.dash.pill(v, kumar.dash.status_colour(v)),
				},
			],
			d.open_orders,
			{
				sort_key: "transaction_date",
				empty: __("Every order has been received and billed."),
				on_click: (r) => frappe.set_route("Form", "Purchase Order", r.name),
			}
		);

		// ---- invoices
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
			{ key: "supplier", label: __("Supplier"), sort: "text" },
			{
				key: "bill_no",
				label: __("Bill No"),
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
						? `<span class="kd-num" style="color:#c2354a">${money(v)}</span>`
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
			kumar.dash.table($body.find("#pa-invoices"), columns, rows, {
				sort_key: "posting_date",
				empty: __("No supplier invoices match."),
				on_click: (r) => frappe.set_route("Form", "Purchase Invoice", r.name),
			});

		draw(d.invoices);

		$body.find(".pa-search").on("input", function () {
			const q = ($(this).val() || "").toLowerCase();
			draw(
				(d.invoices || []).filter(
					(r) =>
						!q ||
						String(r.supplier || "").toLowerCase().includes(q) ||
						String(r.bill_no || "").toLowerCase().includes(q) ||
						String(r.name || "").toLowerCase().includes(q)
				)
			);
		});
	}

	const [f0, t0] = bar.get();
	load(f0, t0);
};
