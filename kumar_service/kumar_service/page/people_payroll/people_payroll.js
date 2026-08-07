// Who works here, who turned up, and what the month cost.

frappe.pages["people-payroll"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("People & Payroll"),
		single_column: true,
	});

	const $main = $(wrapper).find(".layout-main-section");
	const $body = $('<div class="kd-wrap"></div>');
	let latest = null;

	const bar = kumar.dash.date_bar(page, load, "this_month");
	$main.append($body);

	page.set_secondary_action(__("Refresh"), () => {
		const [f, t] = bar.get();
		load(f, t);
	});

	const STAFF_COLUMNS = [
		{ key: "name", label: __("ID") },
		{ key: "employee_name", label: __("Name") },
		{ key: "designation", label: __("Designation") },
		{ key: "department", label: __("Department") },
		{ key: "grade", label: __("Grade") },
		{ key: "branch", label: __("Branch") },
		{ key: "shift", label: __("Shift") },
		{ key: "date_of_joining", label: __("Joined") },
		{ key: "base", label: __("Monthly Base") },
		{ key: "last_net_pay", label: __("Last Net Pay") },
	];

	page.add_menu_item(__("Export Employee List (CSV)"), () => {
		if (latest) kumar.dash.csv("kumar-employees.csv", STAFF_COLUMNS, latest.employees);
	});
	page.add_menu_item(__("Open Salary Slips"), () =>
		frappe.set_route("List", "Salary Slip")
	);
	page.add_menu_item(__("Open Attendance"), () =>
		frappe.set_route("List", "Attendance")
	);

	function load(from_date, to_date) {
		kumar.dash.load(
			$body,
			"kumar_service.dashboard.people_overview",
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
			<div id="pp-tiles"></div>

			<div class="kd-grid">
				${kumar.dash.card(__("People at Work, by Day"), "pp-attendance", 8)}
				${kumar.dash.card(__("Attendance Mix"), "pp-mix", 4)}
			</div>

			<div class="kd-grid">
				${kumar.dash.card(__("Headcount by Department"), "pp-dept", 6)}
				${kumar.dash.card(__("Wage Bill by Department"), "pp-cost", 6)}
			</div>

			<div class="kd-grid">
				${kumar.dash.card(__("Headcount by Grade"), "pp-grade", 4)}
				${kumar.dash.card(__("Payroll Runs"), "pp-runs", 4)}
				${kumar.dash.card(__("Most Absences"), "pp-absent", 4)}
			</div>

			${kumar.dash.section(
				__("Employee List"),
				"pp-staff",
				`<input type="search" class="form-control input-sm pp-search"
					placeholder="${__("Filter by name, role or department")}" style="width:250px">`
			)}
		`);

		kumar.dash.tiles($body.find("#pp-tiles"), [
			{
				label: __("Headcount"),
				value: num(t.headcount),
				hint: __("Across {0} departments", [num(t.departments)]),
				tone: "info",
				big: true,
			},
			{
				label: __("Attendance"),
				value: kumar.dash.pct(t.attendance_pct),
				hint: __("{0} days marked", [num(t.attendance_marked)]),
				tone: t.attendance_pct >= 92 ? "good" : "warn",
			},
			{
				label: __("Absent Days"),
				value: num(t.absent),
				hint: __("{0} on approved leave", [num(t.on_leave)]),
				tone: "warn",
			},
			{
				label: __("Gross Wage Bill"),
				value: money(t.gross),
				title: kumar.dash.rupees(t.gross),
				hint: t.payroll_month
					? __("Payroll for {0}", [kumar.dash.date(t.payroll_month)])
					: __("Latest payroll run"),
				tone: "warn",
			},
			{
				label: __("Deductions"),
				value: money(t.deductions),
				title: kumar.dash.rupees(t.deductions),
				hint: __("PF, ESI and taxes"),
			},
			{
				label: __("Net Paid"),
				value: money(t.net),
				title: kumar.dash.rupees(t.net),
				hint: __("{0} salary slips", [num(t.slips)]),
				tone: "good",
			},
			{
				label: __("Average Gross"),
				value: money(t.avg_ctc),
				title: kumar.dash.rupees(t.avg_ctc),
				hint: __("Per person per month"),
			},
		]);

		// ---- attendance trend
		const att = d.attendance_series || {};
		kumar.dash.chart($body.find("#pp-attendance"), {
			type: "line",
			fill: true,
			labels: att.labels,
			datasets: [{ name: __("At work"), values: att.values }],
			colors: ["#2e9e5b"],
		});

		// ---- mix
		const mix = d.attendance_mix || [];
		kumar.dash.chart($body.find("#pp-mix"), {
			type: "donut",
			series: false,
			height: 250,
			labels: mix.map((m) => m.status),
			datasets: [{ name: __("Days"), values: mix.map((m) => m.n) }],
		});

		// ---- department headcount
		const dept = d.by_department || [];
		kumar.dash.chart($body.find("#pp-dept"), {
			type: "bar",
			series: false,
			height: 260,
			labels: dept.map((x) => String(x.department).replace(/ - \w+$/, "")),
			datasets: [{ name: __("People"), values: dept.map((x) => x.headcount) }],
		});

		// ---- wage bill by department
		kumar.dash.table(
			$body.find("#pp-cost"),
			[
				{
					key: "department",
					label: __("Department"),
					sort: "text",
					format: (v) => kumar.dash.esc(String(v).replace(/ - \w+$/, "")),
				},
				{
					key: "slips",
					label: __("People"),
					align: "right",
					format: (v) => `<span class="kd-num">${num(v)}</span>`,
				},
				{
					key: "gross",
					label: __("Gross"),
					align: "right",
					format: (v) =>
						`<span class="kd-num" title="${kumar.dash.rupees(v)}">${money(v)}</span>`,
				},
				{
					key: "net",
					label: __("Net"),
					align: "right",
					format: (v) =>
						`<span class="kd-num" title="${kumar.dash.rupees(v)}">${money(v)}</span>`,
				},
			],
			d.payroll_by_department,
			{ sort_key: "net", empty: __("No payroll has been run yet.") }
		);

		// ---- grade
		const grade = d.by_grade || [];
		kumar.dash.chart($body.find("#pp-grade"), {
			type: "bar",
			series: false,
			height: 240,
			labels: grade.map((g) => g.grade),
			datasets: [{ name: __("People"), values: grade.map((g) => g.headcount) }],
			colors: ["#8b3fa8"],
		});

		// ---- payroll runs
		kumar.dash.table(
			$body.find("#pp-runs"),
			[
				{
					key: "start_date",
					label: __("Month"),
					sort: "text",
					format: (v) => kumar.dash.date(v),
				},
				{
					key: "slips",
					label: __("Slips"),
					align: "right",
					format: (v) => `<span class="kd-num">${num(v)}</span>`,
				},
				{
					key: "net",
					label: __("Net Paid"),
					align: "right",
					format: (v) =>
						`<span class="kd-num" title="${kumar.dash.rupees(v)}">${money(v)}</span>`,
				},
			],
			d.payroll_runs,
			{ sort_key: "start_date", empty: __("No payroll has been run yet.") }
		);

		// ---- absences
		kumar.dash.table(
			$body.find("#pp-absent"),
			[
				{ key: "employee_name", label: __("Employee"), sort: "text" },
				{
					key: "absent",
					label: __("Absent"),
					align: "right",
					format: (v) => `<span class="kd-num" style="color:#c2354a">${num(v)}</span>`,
				},
				{
					key: "on_leave",
					label: __("Leave"),
					align: "right",
					format: (v) => `<span class="kd-num">${num(v)}</span>`,
				},
			],
			d.top_absent,
			{
				sort_key: "absent",
				empty: __("Nobody was absent in this period."),
				on_click: (r) => frappe.set_route("Form", "Employee", r.employee),
			}
		);

		// ---- the roll
		const columns = [
			{
				key: "employee_name",
				label: __("Name"),
				sort: "text",
				format: (v, r) =>
					`<b>${kumar.dash.esc(v)}</b> <span class="text-muted">${kumar.dash.esc(
						r.name
					)}</span>`,
			},
			{ key: "designation", label: __("Designation"), sort: "text" },
			{
				key: "department",
				label: __("Department"),
				sort: "text",
				format: (v) => kumar.dash.esc(String(v || "").replace(/ - \w+$/, "")),
			},
			{ key: "grade", label: __("Grade"), sort: "text", align: "center" },
			{ key: "branch", label: __("Branch"), sort: "text" },
			{
				key: "shift",
				label: __("Shift"),
				sort: "text",
				format: (v) => kumar.dash.esc(v || "-"),
			},
			{
				key: "date_of_joining",
				label: __("Joined"),
				sort: "text",
				format: (v) => kumar.dash.date(v),
			},
			{
				key: "base",
				label: __("Monthly Base"),
				align: "right",
				format: (v) => `<span class="kd-num">${kumar.dash.rupees(v)}</span>`,
			},
			{
				key: "last_net_pay",
				label: __("Last Net Pay"),
				align: "right",
				format: (v) =>
					v
						? `<span class="kd-num">${kumar.dash.rupees(v)}</span>`
						: `<span class="text-muted">-</span>`,
			},
		];

		const draw = (rows) =>
			kumar.dash.table($body.find("#pp-staff"), columns, rows, {
				sort_key: "employee_name",
				sort_dir: "asc",
				empty: __("No employees match."),
				on_click: (r) => frappe.set_route("Form", "Employee", r.name),
			});

		draw(d.employees);

		$body.find(".pp-search").on("input", function () {
			const q = ($(this).val() || "").toLowerCase();
			draw(
				(d.employees || []).filter(
					(r) =>
						!q ||
						String(r.employee_name || "").toLowerCase().includes(q) ||
						String(r.designation || "").toLowerCase().includes(q) ||
						String(r.department || "").toLowerCase().includes(q) ||
						String(r.grade || "").toLowerCase().includes(q)
				)
			);
		});
	}

	const [f0, t0] = bar.get();
	load(f0, t0);
};
