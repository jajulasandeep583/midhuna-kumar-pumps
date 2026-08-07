// Head office's view of the distribution network.
//
// The question here is comparative: which dealers are carrying the month,
// which have stopped selling, and where are the pumps actually landing. That
// needs rows and rankings - which is exactly what a dealer does NOT need, so
// the dealer's own screen (my-business) is a separate, much simpler page.

frappe.pages["dealer-network"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Dealer Network"),
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

	page.add_menu_item(__("Export Dealers (CSV)"), () => {
		if (!latest) return;
		kumar.dash.csv("kumar-dealers.csv", DEALER_COLUMNS, latest.dealers);
	});
	page.add_menu_item(__("Open Dealer Tree"), () => frappe.set_route("Tree", "Dealer"));

	const DEALER_COLUMNS = [
		{ key: "dealer_name", label: __("Dealer") },
		{ key: "channel", label: __("Whose Invoice") },
		{ key: "dealer_type", label: __("Type") },
		{ key: "city", label: __("City") },
		{ key: "state", label: __("State") },
		{ key: "contact_person", label: __("Contact") },
		{ key: "mobile_no", label: __("Mobile") },
		{ key: "registrations", label: __("Sold") },
		{ key: "registrations_prev", label: __("Sold Prev Period") },
		{ key: "growth_pct", label: __("Growth %") },
		{ key: "revenue", label: __("Revenue") },
		{ key: "avg_ticket", label: __("Avg per Pump") },
		{ key: "outstanding", label: __("Outstanding") },
		{ key: "complaints", label: __("Complaints") },
		{ key: "complaint_rate_pct", label: __("Fault %") },
		{ key: "claims", label: __("Claims") },
		{ key: "expiring_30d", label: __("Warranty Expiring 30d") },
		{ key: "last_sale_date", label: __("Last Sale") },
		{ key: "days_since_sale", label: __("Days Since Sale") },
	];

	function load(from_date, to_date) {
		kumar.dash.load(
			$body,
			"kumar_service.dashboard.dealer_distribution",
			{ from_date, to_date },
			render
		);
	}

	function render(d) {
		latest = d;
		const totals = d.totals || {};
		const money = kumar.dash.money;
		const num = kumar.dash.num;

		$body.html(`
			<div id="dn-tiles"></div>
			<div class="kd-grid">
				${kumar.dash.card(__("Units per Day, by Channel"), "dn-trend", 8)}
				${kumar.dash.card(__("Who Sold Them"), "dn-channel", 4)}
			</div>
			<div class="kd-grid">
				${kumar.dash.card(__("Sales by Dealer Tier"), "dn-tier", 4)}
				${kumar.dash.card(__("Where the Pumps Went"), "dn-geo", 4)}
				${kumar.dash.card(__("What They Are Used For"), "dn-app", 4)}
			</div>
			${kumar.dash.section(__("Top Ten This Period"), "dn-top")}
			<div id="dn-quiet-wrap"></div>
			${kumar.dash.section(
				__("Every Dealer in the Network"),
				"dn-table",
				`<input type="search" class="form-control input-sm dn-search"
					placeholder="${__("Filter by name or city")}" style="width:220px">`
			)}
		`);

		// "vs the month before" where there IS a month before, and nothing at
		// all where there is not - an invented +100% reads as a real doubling
		const vs = (pct, prev) =>
			pct === null || pct === undefined
				? __("No earlier period to compare")
				: `${kumar.dash.delta(pct)} ${__("vs {0} before", [num(prev)])}`;

		const byChannel = {};
		(d.channels || []).forEach((c) => (byChannel[c.channel] = c));
		const indep = byChannel["Independent"] || {};
		const branch = byChannel["KUMAR Branch"] || {};

		kumar.dash.tiles($body.find("#dn-tiles"), [
			{
				label: __("Pumps Sold"),
				value: num(totals.registrations),
				hint: vs(totals.growth_pct, totals.registrations_prev),
				tone: "good",
				big: true,
			},
			{
				label: __("Revenue"),
				value: money(totals.revenue),
				title: kumar.dash.rupees(totals.revenue),
				hint: vs(totals.revenue_growth_pct, totals.revenue_prev),
				tone: "good",
			},
			{
				label: __("Through Dealers"),
				value: num(indep.units),
				hint: __("{0} independent firms &middot; {1}", [
					num(indep.dealers),
					money(indep.revenue),
				]),
				tone: "info",
			},
			{
				label: __("Over Our Counter"),
				value: num(branch.units),
				hint: __("{0} KUMAR branches &middot; {1}", [
					num(branch.dealers),
					money(branch.revenue),
				]),
				tone: "info",
			},
			{
				label: __("Outstanding"),
				value: money(totals.outstanding),
				title: kumar.dash.rupees(totals.outstanding),
				hint: __("Across the whole network"),
				tone: totals.outstanding > 0 ? "warn" : "flat",
			},
			{
				label: __("Selling / Silent"),
				value: `${num(totals.selling)} / ${num(totals.silent)}`,
				hint: totals.silent
					? __("{0} sold nothing - worth a call", [num(totals.silent)])
					: __("Every outlet moved stock"),
				tone: totals.silent ? "bad" : "good",
			},
		]);

		// ---- units per day, one line per channel
		const tr = d.trend || { days: [], series: {} };
		kumar.dash.chart($body.find("#dn-trend"), {
			type: "line",
			height: 240,
			fill: true,
			labels: tr.days,
			datasets: Object.keys(tr.series || {}).map((k) => ({
				name: k,
				values: tr.series[k],
			})),
			colors: ["#0b5394", "#e0781a"],
		});

		// ---- the split itself
		kumar.dash.chart($body.find("#dn-channel"), {
			type: "donut",
			series: false,
			height: 240,
			labels: (d.channels || []).map((c) => c.channel),
			datasets: [{ name: __("Units"), values: (d.channels || []).map((c) => c.units) }],
			colors: ["#e0781a", "#0b5394"],
		});

		// ---- tier mix
		const tiers = d.by_type || [];
		kumar.dash.chart($body.find("#dn-tier"), {
			type: "bar",
			series: false,
			height: 220,
			labels: tiers.map((t) => t.dealer_type),
			datasets: [{ name: __("Units"), values: tiers.map((t) => t.registrations) }],
		});

		// ---- geography: a ranked bar reads better than a map nobody can click
		const geo = (d.geography || []).slice(0, 10);
		kumar.dash.chart($body.find("#dn-geo"), {
			type: "bar",
			series: false,
			height: 220,
			labels: geo.map((g) => g.district),
			datasets: [{ name: __("Units"), values: geo.map((g) => g.units) }],
			colors: ["#e0781a"],
		});

		// ---- application mix
		const app = d.application_mix || [];
		kumar.dash.chart($body.find("#dn-app"), {
			type: "percentage",
			series: false,
			height: 220,
			labels: app.map((a) => a.application),
			datasets: [{ name: __("Units"), values: app.map((a) => a.units) }],
		});

		// ---- top ten: a bar is faster to read than a ranked table
		const top = (d.leaderboard || []).slice().reverse();
		kumar.dash.chart($body.find("#dn-top"), {
			type: "bar",
			series: false,
			height: Math.max(220, top.length * 26),
			labels: top.map((r) => r.dealer_name),
			datasets: [{ name: __("Pumps Sold"), values: top.map((r) => r.registrations) }],
			colors: ["#2e9e5b"],
		});

		// ---- who to ring. Only worth a section when there is somebody on it.
		const quiet = d.needs_a_call || [];
		if (quiet.length) {
			$body.find("#dn-quiet-wrap").html(
				kumar.dash.section(__("Sold Nothing This Period"), "dn-quiet")
			);
			kumar.dash.table(
				$body.find("#dn-quiet"),
				[
					{ key: "dealer_name", label: __("Dealer"), sort: "text" },
					{ key: "city", label: __("City"), sort: "text" },
					{ key: "contact_person", label: __("Contact"), sort: "text" },
					{
						key: "mobile_no",
						label: __("Mobile"),
						format: (v) =>
							v
								? `<a href="tel:${kumar.dash.esc(v)}">${kumar.dash.esc(v)}</a>`
								: `<span class="text-muted">-</span>`,
					},
					{
						key: "days_since_sale",
						label: __("Days Since Last Sale"),
						align: "right",
						format: (v) =>
							v === null || v === undefined
								? `<span class="text-muted">${__("never sold")}</span>`
								: `<span class="kd-num" style="color:#c2354a">${kumar.dash.num(v)}</span>`,
					},
				],
				quiet,
				{
					sort_key: "days_since_sale",
					on_click: (row) => frappe.set_route("Form", "Dealer", row.name),
				}
			);
		}

		// ---- the table
		const columns = [
			{
				key: "dealer_name",
				label: __("Dealer"),
				sort: "text",
				format: (v, row) =>
					`<b>${kumar.dash.esc(v || row.name)}</b>${
						row.is_group ? ` <span class="text-muted">(${__("group")})</span>` : ""
					}`,
			},
			{
				key: "channel",
				label: __("Whose Invoice"),
				sort: "text",
				format: (v) =>
					v === "KUMAR Branch"
						? kumar.dash.pill(__("Ours"), "blue")
						: kumar.dash.pill(__("Dealer's"), "orange"),
			},
			{ key: "dealer_type", label: __("Type"), sort: "text" },
			{
				key: "city",
				label: __("City"),
				sort: "text",
				format: (v, row) =>
					kumar.dash.esc([v, row.state].filter(Boolean).join(", ")),
			},
			{
				key: "registrations",
				label: __("Sold"),
				align: "right",
				format: (v) => `<span class="kd-num">${kumar.dash.num(v)}</span>`,
			},
			{
				key: "growth_pct",
				label: __("vs Prev"),
				align: "right",
				format: (v, row) =>
					v === null || v === undefined
						? `<span class="text-muted">${row.registrations ? __("new") : "-"}</span>`
						: kumar.dash.delta(v),
			},
			{
				key: "days_since_sale",
				label: __("Last Sale"),
				align: "right",
				format: (v) => {
					if (v === null || v === undefined)
						return `<span class="text-muted">${__("never")}</span>`;
					const colour = v > 30 ? "#c2354a" : v > 14 ? "#b06000" : "var(--text-muted)";
					return `<span class="kd-num" style="color:${colour}">${__("{0}d ago", [
						kumar.dash.num(v),
					])}</span>`;
				},
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
			{
				key: "outstanding",
				label: __("Outstanding"),
				align: "right",
				format: (v) =>
					v > 0
						? `<span class="kd-num" style="color:#c2354a" title="${kumar.dash.rupees(
								v
						  )}">${kumar.dash.money(v)}</span>`
						: `<span class="text-muted">-</span>`,
			},
			{
				key: "avg_ticket",
				label: __("Avg / Pump"),
				align: "right",
				format: (v) =>
					v
						? `<span class="kd-num" title="${kumar.dash.rupees(v)}">${kumar.dash.money(
								v
						  )}</span>`
						: `<span class="text-muted">-</span>`,
			},
			{
				key: "expiring_30d",
				label: __("Expiring 30d"),
				align: "right",
				format: (v) =>
					v
						? `<span class="kd-num" style="color:#b06000">${kumar.dash.num(v)}</span>`
						: `<span class="text-muted">-</span>`,
			},
			{
				key: "complaints",
				label: __("Complaints"),
				align: "right",
				format: (v) => `<span class="kd-num">${kumar.dash.num(v)}</span>`,
			},
			{
				key: "complaint_rate_pct",
				label: __("Fault %"),
				align: "right",
				format: (v) => {
					const colour = v > 8 ? "#c2354a" : v > 4 ? "#b06000" : "var(--text-muted)";
					return `<span class="kd-num" style="color:${colour}">${kumar.dash.pct(v)}</span>`;
				},
			},
			{
				key: "claims",
				label: __("Claims"),
				align: "right",
				format: (v) => `<span class="kd-num">${kumar.dash.num(v)}</span>`,
			},
		];

		const draw = (rows) =>
			kumar.dash.table($body.find("#dn-table"), columns, rows, {
				sort_key: "revenue",
				empty: __("No dealers match."),
				on_click: (row) => frappe.set_route("Form", "Dealer", row.name),
			});

		draw(d.dealers);

		$body.find(".dn-search").on("input", function () {
			const q = ($(this).val() || "").toLowerCase();
			draw(
				(d.dealers || []).filter(
					(r) =>
						!q ||
						String(r.dealer_name || "").toLowerCase().includes(q) ||
						String(r.city || "").toLowerCase().includes(q)
				)
			);
		});
	}

	const [f0, t0] = bar.get();
	load(f0, t0);
};
