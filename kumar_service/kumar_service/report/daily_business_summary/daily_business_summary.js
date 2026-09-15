// Daily Business Summary - three cards (Sales, Purchases, Cash Flow) drawn over
// the report's own rows; every figure opens the documents behind it.

frappe.query_reports["Daily Business Summary"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
	],

	onload: function () {
		if (document.getElementById("dbs-style")) return;
		var s = document.createElement("style");
		s.id = "dbs-style";
		s.textContent = `
			.dbs-wrap {
				display: grid;
				grid-template-columns: repeat(3, 1fr);
				gap: 14px;
				padding: 16px 0 4px;
			}
			@media (max-width: 900px) { .dbs-wrap { grid-template-columns: 1fr; } }

			.dbs-card { border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; background: var(--card-bg); }

			.dbs-head { padding: 10px 16px; font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; display: flex; align-items: center; gap: 6px; }
			.dbs-head.green { background: rgba(46,204,113,0.08); color: #27ae60; border-bottom: 2px solid #2ecc71; }
			.dbs-head.red   { background: rgba(231,76,60,0.08);  color: #c0392b; border-bottom: 2px solid #e74c3c; }
			.dbs-head.blue  { background: rgba(52,152,219,0.08); color: #2980b9; border-bottom: 2px solid #3498db; }

			.dbs-row { display: flex; justify-content: space-between; align-items: center; padding: 9px 16px; border-bottom: 1px solid var(--border-color); transition: background 0.15s; }
			.dbs-row.nav { cursor: pointer; }
			.dbs-row.nav:hover { background: var(--fg-hover-color, rgba(0,0,0,0.04)); }

			.dbs-sub-label { font-size: 10px; color: var(--text-light, #aaa); background: var(--control-bg); padding: 1px 5px; border-radius: 3px; margin-left: 4px; }

			.dbs-foot { display: flex; justify-content: space-between; align-items: center; padding: 9px 16px; background: var(--control-bg); border-top: 2px solid var(--border-color); transition: filter 0.15s; }
			.dbs-foot.nav { cursor: pointer; }
			.dbs-foot.nav:hover { filter: brightness(0.94); }

			.dbs-lbl { font-size: 12px; color: var(--text-muted); display: flex; align-items: center; gap: 5px; }
			.dbs-arr { font-size: 10px; color: #bbb; }
			.dbs-right { display: flex; align-items: baseline; gap: 7px; }
			.dbs-cnt { font-size: 10px; color: var(--text-muted); background: var(--control-bg); padding: 1px 6px; border-radius: 3px; font-weight: 600; }
			.dbs-val { font-size: 14px; font-weight: 700; font-family: monospace; }
			.dbs-val.green { color: #27ae60; }
			.dbs-val.red   { color: #c0392b; }
			.dbs-val.amber { color: #e67e22; }
			.dbs-val.blue  { color: #2980b9; }

			.dbs-foot-lbl { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); display: flex; align-items: center; gap: 5px; }
			.dbs-foot-val { font-size: 15px; font-weight: 700; font-family: monospace; }
			.dbs-foot-val.green { color: #27ae60; }
			.dbs-foot-val.red   { color: #c0392b; }
			.dbs-foot-val.amber { color: #e67e22; }
			.dbs-foot-val.blue  { color: #2980b9; }

			.dbs-divider { height: 1px; background: var(--border-color); margin: 0 16px; opacity: 0.5; }
		`;
		document.head.appendChild(s);
	},

	after_datatable_render: function () {
		this.render_cards();
	},

	render_cards: function () {
		// Everything is looked up inside THIS report's wrapper: frappe keeps the
		// pages you visited earlier in the DOM, and a bare document.querySelector
		// can land on another report's table.
		var host = frappe.query_report.$report && frappe.query_report.$report[0];
		if (!host) return;
		var old = host.querySelector(".dbs-wrap");
		if (old) old.remove();

		var data = frappe.query_report.data || [];
		var get = function (t) {
			return data.find(function (r) { return r.row_type === t; }) || {};
		};

		var si = get("sales");
		var so = get("info_so");
		var rv = get("total_recv");
		var pi = get("purchase");
		var po = get("info_po");
		var py_ = get("total_pay");
		var cl = get("collection");
		var jc = get("je_collection");
		var pm = get("payment");
		var jp = get("je_payment");
		var nt = get("net");

		var company = frappe.query_report.get_filter_value("company") || "";
		var fd = frappe.query_report.get_filter_value("from_date") || "";
		var td = frappe.query_report.get_filter_value("to_date") || "";
		var netColor = parseFloat(nt.amount || 0) >= 0 ? "blue" : "red";
		var dateRange = ["between", [fd, td]];

		function fmt(n) {
			if (n === null || n === undefined) return "—";
			n = parseFloat(n) || 0;
			var abs = Math.abs(n), sign = n < 0 ? "-" : "";
			if (abs >= 1e7) return sign + "₹" + (abs / 1e7).toFixed(2) + " Cr";
			if (abs >= 1e5) return sign + "₹" + (abs / 1e5).toFixed(2) + " L";
			if (abs >= 1e3) return sign + "₹" + (abs / 1e3).toFixed(1) + "K";
			return sign + "₹" + abs.toFixed(0);
		}

		var navHandlers = [];

		function row(label, sublabel, val, color, count, navFn) {
			var idx = navHandlers.length;
			navHandlers.push(navFn || null);
			var cls = navFn ? " nav" : "";
			var arr = navFn ? '<span class="dbs-arr">↗</span>' : "";
			var sub = sublabel ? '<span class="dbs-sub-label">' + sublabel + "</span>" : "";
			var cnt = count ? '<span class="dbs-cnt">' + count + "</span>" : "";
			return '<div class="dbs-row' + cls + '" data-dbs="' + idx + '">'
				+ '<span class="dbs-lbl">' + label + sub + arr + "</span>"
				+ '<div class="dbs-right">' + cnt
				+ '<span class="dbs-val ' + color + '">' + fmt(val) + "</span>"
				+ "</div></div>";
		}

		function foot(label, val, color, navFn) {
			var idx = navHandlers.length;
			navHandlers.push(navFn || null);
			var cls = navFn ? " nav" : "";
			var arr = navFn ? '<span class="dbs-arr">↗</span>' : "";
			return '<div class="dbs-foot' + cls + '" data-dbs="' + idx + '">'
				+ '<span class="dbs-foot-lbl">' + label + arr + "</span>"
				+ '<span class="dbs-foot-val ' + color + '">' + fmt(val) + "</span>"
				+ "</div>";
		}

		var salesHtml = '<div class="dbs-card">'
			+ '<div class="dbs-head green">💹 ' + __("Sales") + "</div>"
			+ row(__("Invoices"), "", si.amount, "green", si.count, function () {
				frappe.route_options = { docstatus: 1, company: company, posting_date: dateRange };
				frappe.set_route("List", "Sales Invoice");
			})
			+ row(__("Pending Orders"), "", so.amount, "amber", so.count, function () {
				frappe.route_options = { docstatus: 1, company: company, status: "To Deliver and Bill" };
				frappe.set_route("List", "Sales Order");
			})
			// the original pointed at an "Accounts Receivable-RBOL" copy that only
			// exists on the site it came from; the standard report is the same thing
			+ foot(__("Total Receivable"), rv.amount, "amber", function () {
				frappe.route_options = { company: company };
				frappe.set_route("query-report", "Accounts Receivable");
			})
			+ "</div>";

		var purchHtml = '<div class="dbs-card">'
			+ '<div class="dbs-head red">🛒 ' + __("Purchases") + "</div>"
			+ row(__("Invoices"), "", pi.amount, "red", pi.count, function () {
				frappe.route_options = { docstatus: 1, company: company, posting_date: dateRange };
				frappe.set_route("List", "Purchase Invoice");
			})
			+ row(__("Pending Orders"), "", po.amount, "amber", po.count, function () {
				frappe.route_options = { docstatus: 1, company: company, status: "To Receive and Bill" };
				frappe.set_route("List", "Purchase Order");
			})
			+ foot(__("Total Payable"), py_.amount, "amber", function () {
				frappe.route_options = { company: company };
				frappe.set_route("query-report", "Accounts Payable");
			})
			+ "</div>";

		var cashHtml = '<div class="dbs-card">'
			+ '<div class="dbs-head blue">💰 ' + __("Cash Flow") + "</div>"
			+ row(__("Collections"), "PE", cl.amount, "green", cl.count, function () {
				frappe.route_options = { docstatus: 1, company: company, payment_type: "Receive", posting_date: dateRange };
				frappe.set_route("List", "Payment Entry");
			})
			+ row(__("Collections"), "JE", jc.amount, "green", jc.count, function () {
				frappe.route_options = { company: company, posting_date: dateRange };
				frappe.set_route("List", "Journal Entry");
			})
			+ '<div class="dbs-divider"></div>'
			+ row(__("Payments Out"), "PE", pm.amount, "red", pm.count, function () {
				frappe.route_options = { docstatus: 1, company: company, payment_type: "Pay", posting_date: dateRange };
				frappe.set_route("List", "Payment Entry");
			})
			+ row(__("Payments Out"), "JE", jp.amount, "red", jp.count, function () {
				frappe.route_options = { company: company, posting_date: dateRange };
				frappe.set_route("List", "Journal Entry");
			})
			+ foot(__("Net Cash Flow"), nt.amount, netColor, null)
			+ "</div>";

		var dt = host.querySelector(".datatable");
		if (!dt) return;
		dt.insertAdjacentHTML("beforebegin",
			'<div class="dbs-wrap">' + salesHtml + purchHtml + cashHtml + "</div>");

		host.querySelectorAll("[data-dbs]").forEach(function (el) {
			var fn = navHandlers[parseInt(el.getAttribute("data-dbs"), 10)];
			if (fn) el.addEventListener("click", fn);
		});

		// The cards are the report; the raw rows under them are hidden. Hide the
		// table itself, not its parent: in v16 the parent is .report-wrapper,
		// which also holds the cards just inserted.
		dt.style.display = "none";
	},
};
