// Shared furniture for the management screens.
//
// Six pages ask different questions of the same month, but they should all
// look and behave like one product: same tiles, same date bar, same tables,
// same money formatting. That lives here rather than being copied six times.

window.kumar = window.kumar || {};
kumar.dash = kumar.dash || {};

// ---------------------------------------------------------------- numbers

// Indian money reads in lakhs and crores. A tile showing "1,24,80,000" is
// unreadable at a glance; "Rs 1.25 Cr" is not. Full value stays in the title.
kumar.dash.money = function (value, decimals) {
	const n = Number(value || 0);
	const sign = n < 0 ? "-" : "";
	const abs = Math.abs(n);
	if (abs >= 1e7) return `${sign}₹${(abs / 1e7).toFixed(decimals ?? 2)} Cr`;
	if (abs >= 1e5) return `${sign}₹${(abs / 1e5).toFixed(decimals ?? 2)} L`;
	if (abs >= 1e3) return `${sign}₹${(abs / 1e3).toFixed(decimals ?? 1)} K`;
	return `${sign}₹${abs.toFixed(0)}`;
};

kumar.dash.rupees = function (value) {
	return format_currency(Number(value || 0), "INR");
};

kumar.dash.num = function (value) {
	return Number(value || 0).toLocaleString("en-IN");
};

kumar.dash.pct = function (value, decimals) {
	if (value === null || value === undefined) return "-";
	return `${Number(value).toFixed(decimals ?? 1)}%`;
};

kumar.dash.esc = function (value) {
	return frappe.utils.escape_html(String(value ?? ""));
};

kumar.dash.date = function (value) {
	return value ? frappe.datetime.str_to_user(value) : "";
};

// -------------------------------------------------------------- date bar

// Presets first, custom dates second. Nobody wants to type two dates to see
// "this month".
kumar.dash.PRESETS = [
	{ key: "this_month", label: __("This Month") },
	{ key: "last_30", label: __("Last 30 Days") },
	{ key: "last_month", label: __("Last Month") },
	{ key: "this_quarter", label: __("This Quarter") },
	{ key: "this_year", label: __("This Financial Year") },
];

kumar.dash.resolve_preset = function (key) {
	const today = frappe.datetime.get_today();
	switch (key) {
		case "last_30":
			return [frappe.datetime.add_days(today, -30), today];
		case "last_month": {
			const first_this = frappe.datetime.month_start();
			const last_prev = frappe.datetime.add_days(first_this, -1);
			return [frappe.datetime.month_start(last_prev), last_prev];
		}
		case "this_quarter":
			return [frappe.datetime.quarter_start(), today];
		case "this_year":
			return [kumar.dash.fy_start(), today];
		case "this_month":
		default:
			return [frappe.datetime.month_start(), today];
	}
};

// India runs April-March. frappe.datetime.year_start() is the calendar year.
kumar.dash.fy_start = function () {
	const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
	const year = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
	return `${year}-04-01`;
};

/**
 * Build the date bar into a page and call `on_change(from, to)` whenever it
 * moves. Returns an object with `.get()` and `.set()`.
 */
kumar.dash.date_bar = function (page, on_change, default_preset) {
	const preset = default_preset || "last_30";
	let [from_date, to_date] = kumar.dash.resolve_preset(preset);

	const $bar = $(`
		<div class="kd-bar">
			<div class="kd-presets"></div>
			<div class="kd-range">
				<input type="date" class="form-control kd-from" value="${from_date}">
				<span class="kd-dash">&rarr;</span>
				<input type="date" class="form-control kd-to" value="${to_date}">
				<button class="btn btn-sm btn-default kd-refresh" title="${__("Refresh")}">
					${frappe.utils.icon("refresh", "sm")}
				</button>
			</div>
		</div>
	`);

	kumar.dash.PRESETS.forEach((p) => {
		$bar.find(".kd-presets").append(
			`<button class="btn btn-sm kd-preset ${p.key === preset ? "kd-on" : ""}"
				data-key="${p.key}">${p.label}</button>`
		);
	});

	const fire = () => on_change(from_date, to_date);

	$bar.on("click", ".kd-preset", function () {
		$bar.find(".kd-preset").removeClass("kd-on");
		$(this).addClass("kd-on");
		[from_date, to_date] = kumar.dash.resolve_preset($(this).data("key"));
		$bar.find(".kd-from").val(from_date);
		$bar.find(".kd-to").val(to_date);
		fire();
	});

	$bar.on("change", ".kd-from, .kd-to", () => {
		from_date = $bar.find(".kd-from").val();
		to_date = $bar.find(".kd-to").val();
		$bar.find(".kd-preset").removeClass("kd-on");
		fire();
	});

	$bar.on("click", ".kd-refresh", fire);

	$(page.wrapper).find(".layout-main-section").append($bar);

	return {
		$el: $bar,
		get: () => [from_date, to_date],
		set: (f, t) => {
			from_date = f;
			to_date = t;
			$bar.find(".kd-from").val(f);
			$bar.find(".kd-to").val(t);
			fire();
		},
	};
};

// ----------------------------------------------------------------- tiles

/**
 * `specs` is an array of {label, value, tone, hint, href, big}.
 * `value` is already-formatted text - formatting is the caller's decision
 * because only the caller knows if a number is money, a count or a rate.
 */
kumar.dash.tiles = function ($into, specs) {
	const html = specs
		.filter(Boolean)
		.map((t) => {
			const tone = t.tone ? ` kd-${t.tone}` : "";
			const hint = t.hint ? `<div class="kd-tile-hint">${t.hint}</div>` : "";
			const body = `
				<div class="kd-tile-label">${t.label}</div>
				<div class="kd-tile-value${t.big ? " kd-big" : ""}" title="${t.title || ""}">${t.value}</div>
				${hint}`;
			return t.href
				? `<a class="kd-tile${tone} kd-link" href="${t.href}">${body}</a>`
				: `<div class="kd-tile${tone}">${body}</div>`;
		})
		.join("");
	$into.html(`<div class="kd-tiles">${html}</div>`);
};

// ---------------------------------------------------------------- charts

kumar.dash.COLORS = ["#0b5394", "#2e9e5b", "#e0781a", "#8b3fa8", "#c2354a", "#0f8b9e"];

/**
 * Thin wrapper over frappe.Chart. Destroys any previous chart in the same
 * container first - re-rendering on every date change otherwise stacks
 * canvases on top of each other.
 */
kumar.dash.chart = function ($into, options) {
	$into.empty();
	const node = $into[0];
	if (!node) return null;
	try {
		return new frappe.Chart(node, {
			type: options.type || "line",
			height: options.height || 240,
			animate: false,
			axisOptions: { xIsSeries: options.series !== false, shortenYAxisNumbers: 1 },
			lineOptions: { regionFill: options.fill ? 1 : 0, hideDots: 1 },
			barOptions: { spaceRatio: 0.3 },
			colors: options.colors || kumar.dash.COLORS,
			tooltipOptions: options.tooltip || {},
			data: {
				labels: options.labels || [],
				datasets: options.datasets || [],
			},
		});
	} catch (e) {
		// a chart failing must never take the screen down with it
		$into.html(`<div class="kd-empty">${__("Chart unavailable")}</div>`);
		return null;
	}
};

// ---------------------------------------------------------------- tables

/**
 * A sortable read-only table.
 *
 * `columns`: [{key, label, align, format(value,row), width, sort}]
 * `rows`:    array of plain objects
 * `options`: {on_click(row), empty, limit, csv}
 */
kumar.dash.table = function ($into, columns, rows, options) {
	options = options || {};
	rows = rows || [];

	if (!rows.length) {
		$into.html(`<div class="kd-empty">${options.empty || __("Nothing in this period.")}</div>`);
		return;
	}

	let sort_key = options.sort_key || null;
	let sort_dir = options.sort_dir || "desc";

	const render = () => {
		let data = rows.slice();
		if (sort_key) {
			const col = columns.find((c) => c.key === sort_key);
			data.sort((a, b) => {
				let x = a[sort_key],
					y = b[sort_key];
				if (col && col.sort === "text") {
					x = String(x ?? "");
					y = String(y ?? "");
					return sort_dir === "asc" ? x.localeCompare(y) : y.localeCompare(x);
				}
				x = Number(x || 0);
				y = Number(y || 0);
				return sort_dir === "asc" ? x - y : y - x;
			});
		}
		if (options.limit) data = data.slice(0, options.limit);

		const head = columns
			.map(
				(c) => `<th class="kd-th text-${c.align || "left"}"
					data-key="${c.key}" ${c.width ? `style="width:${c.width}"` : ""}>
					${c.label}${sort_key === c.key ? (sort_dir === "asc" ? " ▲" : " ▼") : ""}
				</th>`
			)
			.join("");

		const body = data
			.map((row, i) => {
				const cells = columns
					.map((c) => {
						const raw = row[c.key];
						const text = c.format ? c.format(raw, row) : kumar.dash.esc(raw);
						return `<td class="text-${c.align || "left"}">${text}</td>`;
					})
					.join("");
				return `<tr class="kd-row" data-index="${i}">${cells}</tr>`;
			})
			.join("");

		$into.html(`
			<div class="kd-table-wrap">
				<table class="kd-table">
					<thead><tr>${head}</tr></thead>
					<tbody>${body}</tbody>
				</table>
			</div>
		`);

		$into.find(".kd-th").on("click", function () {
			const key = $(this).data("key");
			if (sort_key === key) sort_dir = sort_dir === "asc" ? "desc" : "asc";
			else {
				sort_key = key;
				sort_dir = "desc";
			}
			render();
		});

		if (options.on_click) {
			$into.find(".kd-row").on("click", function () {
				options.on_click(data[$(this).data("index")]);
			});
			$into.find(".kd-row").css("cursor", "pointer");
		}
	};

	render();
};

// --------------------------------------------------------------- sections

kumar.dash.section = function (title, id, extra) {
	return `
		<div class="kd-section">
			<div class="kd-section-head">
				<div class="kd-section-title">${title}</div>
				<div class="kd-section-tools">${extra || ""}</div>
			</div>
			<div id="${id}"></div>
		</div>`;
};

kumar.dash.card = function (title, id, span) {
	return `
		<div class="kd-card" style="grid-column:span ${span || 6}">
			<div class="kd-card-title">${title}</div>
			<div id="${id}"></div>
		</div>`;
};

// ----------------------------------------------------------------- export

kumar.dash.csv = function (filename, columns, rows) {
	const header = columns.map((c) => `"${c.label}"`).join(",");
	const body = (rows || [])
		.map((r) =>
			columns
				.map((c) => {
					const v = r[c.key];
					return `"${String(v ?? "").replace(/"/g, '""')}"`;
				})
				.join(",")
		)
		.join("\n");
	const blob = new Blob([`${header}\n${body}`], { type: "text/csv;charset=utf-8;" });
	const link = document.createElement("a");
	link.href = URL.createObjectURL(blob);
	link.download = filename;
	link.click();
	URL.revokeObjectURL(link.href);
};

// ------------------------------------------------------------------ load

/**
 * Standard fetch-and-render. Shows a skeleton, calls the endpoint, hands the
 * message to `render`, and puts an honest message on screen if it fails
 * rather than leaving the last period's numbers up.
 */
kumar.dash.load = function ($target, method, args, render) {
	$target.html(`<div class="kd-loading">${__("Loading...")}</div>`);
	return frappe
		.call({ method: method, args: args, type: "GET" })
		.then((r) => {
			$target.empty();
			render(r.message || {});
		})
		.catch((e) => {
			const msg =
				(e && e.message) ||
				__("Could not load this screen. You may not have permission for it.");
			$target.html(`<div class="kd-error">${kumar.dash.esc(msg)}</div>`);
		});
};

// ------------------------------------------------------------- indicators

kumar.dash.pill = function (text, colour) {
	return `<span class="indicator-pill ${colour}">${kumar.dash.esc(text)}</span>`;
};

kumar.dash.status_colour = function (status) {
	const map = {
		Paid: "green",
		Completed: "green",
		Closed: "green",
		Submitted: "blue",
		Overdue: "red",
		Cancelled: "red",
		Failed: "red",
		Draft: "gray",
		"Not Started": "gray",
		"In Process": "orange",
		Unpaid: "orange",
		"Partly Paid": "orange",
		Open: "orange",
		"To Bill": "orange",
		"To Receive": "orange",
		"To Receive and Bill": "orange",
	};
	return map[status] || "blue";
};

kumar.dash.delta = function (pct) {
	if (pct === null || pct === undefined) return "";
	const up = Number(pct) >= 0;
	return `<span class="kd-delta ${up ? "kd-up" : "kd-down"}">
		${up ? "▲" : "▼"} ${Math.abs(Number(pct)).toFixed(1)}%</span>`;
};
