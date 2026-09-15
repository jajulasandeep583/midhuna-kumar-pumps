frappe.query_reports["Production and Sales Summary"] = {
	filters: [
		{
			// expressions, never quoted strings - a quoted default reaches the
			// date control as literal text and it opens on a junk date
			default: frappe.datetime.month_start(),
			fieldname: "from_date",
			fieldtype: "Date",
			label: "From Date",
			reqd: 1,
		},
		{
			default: frappe.datetime.get_today(),
			fieldname: "to_date",
			fieldtype: "Date",
			label: "To Date",
			reqd: 1,
		},
		{
			fieldname: "pump_model",
			fieldtype: "Link",
			label: "Pump Model",
			options: "Pump Model",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;

		// the total row reads as a total, not as another model
		if (data.model === "Total") {
			value = `<b>${value}</b>`;
		}
		// a model with more complaints than a twentieth of what was sold is
		// worth a manager's eye, so it gets one
		if (column.fieldname === "complaints" && data.sold && data.complaints) {
			if (data.complaints / data.sold > 0.05) {
				value = `<span style="color:var(--red-600,#b91c1c);font-weight:600">${value}</span>`;
			}
		}
		// built but untested is work that cannot ship
		if (column.fieldname === "tested" && data.built && data.tested < data.built) {
			value = `<span style="color:var(--orange-600,#c2410c)">${value}</span>`;
		}
		return value;
	},
};
