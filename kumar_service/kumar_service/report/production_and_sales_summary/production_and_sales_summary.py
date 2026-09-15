"""What the plant built and the network sold, model by model.

The question a proprietor actually asks is not "how many work orders are open" -
it is "what did we make, what did we sell, what is still sitting, and which
models are coming back". Those four numbers live in four different doctypes, so
until now answering it meant four screens and a calculator.

One row per pump model:

    built          serials manufactured in the window
    tested         of those, how many carry a passed test certificate
    sold           registrations in the window (the dealer's sale, not ours)
    in stock       serials built but never registered - finished goods sitting
    complaints     service requests raised in the window, any age of pump
    claim value    what warranty settled or is being asked to settle

Totals are a real row, so the bottom line reads without adding anything up.
"""

import frappe
from frappe.utils import add_months, cint, flt, getdate, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	to_date = getdate(filters.to_date or nowdate())
	from_date = getdate(filters.from_date or add_months(to_date, -1))

	return get_columns(), get_data(from_date, to_date, filters)


def get_columns():
	return [
		{"fieldname": "model", "label": "Pump Model", "fieldtype": "Link",
			"options": "Pump Model", "width": 190},
		{"fieldname": "category", "label": "Family", "fieldtype": "Data", "width": 150},
		{"fieldname": "built", "label": "Built", "fieldtype": "Int", "width": 80},
		{"fieldname": "tested", "label": "Tested", "fieldtype": "Int", "width": 80},
		{"fieldname": "sold", "label": "Sold", "fieldtype": "Int", "width": 80},
		{"fieldname": "in_stock", "label": "In Stock", "fieldtype": "Int", "width": 90},
		{"fieldname": "dealers", "label": "Dealers Selling", "fieldtype": "Int", "width": 120},
		{"fieldname": "complaints", "label": "Complaints", "fieldtype": "Int", "width": 100},
		{"fieldname": "claim_value", "label": "Warranty Cost", "fieldtype": "Currency",
			"options": "Company:company:default_currency", "width": 130},
	]


def get_data(from_date, to_date, filters):
	model_filter = filters.get("pump_model")

	models = {}

	def row(model):
		# frappe's own test records are prefixed with an underscore, and a
		# historical-import trial left "_KT-MODEL-A" with sixty-three sales on
		# it - which sorted straight to the top of a management report
		if not model or str(model).startswith("_"):
			return None
		if model not in models:
			models[model] = {
				"model": model,
				"category": frappe.db.get_value("Pump Model", model, "pump_category"),
				"built": 0, "tested": 0, "sold": 0, "in_stock": 0,
				"dealers": set(), "complaints": 0, "claim_value": 0.0,
			}
		return models[model]

	# ---------------------------------------------------------------- built
	for s in frappe.get_all(
		"Serial No",
		filters={"custom_manufacturing_date": ["between", [from_date, to_date]]},
		fields=["name", "custom_pump_model", "custom_qc_status"],
		limit_page_length=0,
	):
		r = row(s.custom_pump_model)
		if not r:
			continue
		r["built"] += 1
		if s.custom_qc_status == "Passed":
			r["tested"] += 1

	# ------------------------------------------------------------- in stock
	# built at any time, never registered: finished goods the plant is holding
	for s in frappe.db.sql(
		"""select s.custom_pump_model model, count(*) n
		from `tabSerial No` s
		left join `tabPump Registration` r on r.serial_no = s.name and r.docstatus = 1
		where r.name is null and ifnull(s.custom_pump_model, '') != ''
		group by s.custom_pump_model""",
		as_dict=True,
	):
		r = row(s.model)
		if r:
			r["in_stock"] = cint(s.n)

	# ----------------------------------------------------------------- sold
	for reg in frappe.get_all(
		"Pump Registration",
		filters={"docstatus": 1, "sale_date": ["between", [from_date, to_date]]},
		fields=["pump_model", "dealer"],
		limit_page_length=0,
	):
		r = row(reg.pump_model)
		if not r:
			continue
		r["sold"] += 1
		if reg.dealer:
			r["dealers"].add(reg.dealer)

	# ----------------------------------------------------------- complaints
	for sr in frappe.get_all(
		"Service Request",
		filters={"docstatus": ["<", 2], "reported_on": ["between", [from_date, to_date]]},
		fields=["pump_model"],
		limit_page_length=0,
	):
		r = row(sr.pump_model)
		if r:
			r["complaints"] += 1

	# --------------------------------------------------------- warranty cost
	for c in frappe.get_all(
		"Kumar Warranty Claim",
		filters={"docstatus": ["<", 2], "claim_date": ["between", [from_date, to_date]]},
		fields=["pump_model", "claim_amount", "approved_amount", "workflow_state"],
		limit_page_length=0,
	):
		r = row(c.pump_model)
		if r and c.workflow_state != "Rejected":
			r["claim_value"] += flt(c.approved_amount) or flt(c.claim_amount)

	rows = list(models.values())
	if model_filter:
		rows = [r for r in rows if r["model"] == model_filter]
	for r in rows:
		r["dealers"] = len(r["dealers"])
	# busiest first: what was sold, then what was built
	rows.sort(key=lambda r: (-r["sold"], -r["built"]))

	if rows:
		total = {
			"model": "Total", "category": "",
			"built": sum(r["built"] for r in rows),
			"tested": sum(r["tested"] for r in rows),
			"sold": sum(r["sold"] for r in rows),
			"in_stock": sum(r["in_stock"] for r in rows),
			"dealers": 0,
			"complaints": sum(r["complaints"] for r in rows),
			"claim_value": sum(r["claim_value"] for r in rows),
		}
		rows.append(total)
	return rows
