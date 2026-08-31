"""Stock vs Registration Reconciliation.

Converted from a database Script Report to a standard, file-based one.
Script Reports keep their python in the Report record and run it through
safe_exec, which frappe v16 only permits when server_script_enabled is set
in common_site_config - a bench-wide switch that lets any System Manager on
any site on the bench execute arbitrary python. This report needed none of
that: as a file it is ordinary app code, it travels in git, and it can be
reviewed and tested like everything else.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": "Verdict", "fieldname": "verdict", "fieldtype": "Data", "width": 190},
		{"label": "Serial No", "fieldname": "serial_no", "fieldtype": "Link",
			"options": "Serial No", "width": 200},
		{"label": "Model", "fieldname": "model", "fieldtype": "Link",
			"options": "Pump Model", "width": 140},
		{"label": "Item", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
		{"label": "Built On", "fieldname": "manufactured", "fieldtype": "Date", "width": 100},
		{"label": "Age (Days)", "fieldname": "age_days", "fieldtype": "Int", "width": 90},
		{"label": "QC", "fieldname": "qc", "fieldtype": "Data", "width": 90},
		{"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link",
			"options": "Warehouse", "width": 150},
		{"label": "Shipped On", "fieldname": "shipped_on", "fieldtype": "Date", "width": 100},
		{"label": "Shipped Via", "fieldname": "shipped_via", "fieldtype": "Dynamic Link",
			"options": "voucher_type", "width": 160},
		{"label": "voucher_type", "fieldname": "voucher_type", "fieldtype": "Data",
			"width": 10, "hidden": 1},
		{"label": "Billed To", "fieldname": "billed_to", "fieldtype": "Data", "width": 190},
		{"label": "Dealer", "fieldname": "dealer", "fieldtype": "Link", "options": "Dealer", "width": 190},
		{"label": "What To Do", "fieldname": "action", "fieldtype": "Data", "width": 300},
	]

	GAP = "SHIPPED - NOT REGISTERED"
	ORPHAN = "No stock record at all"
	HELD = "Held - QC not passed"
	STOCK = "In stock - not sold yet"
	DONE = "Registered"

	serial_filter = {}
	if filters.get("pump_model"):
		serial_filter["custom_pump_model"] = filters.get("pump_model")
	if filters.get("item_code"):
		serial_filter["item_code"] = filters.get("item_code")
	if filters.get("from_date") and filters.get("to_date"):
		serial_filter["custom_manufacturing_date"] = [
			"between", [filters.get("from_date"), filters.get("to_date")]
		]

	serials = frappe.get_all("Serial No",
		filters=serial_filter,
		fields=["name", "item_code", "custom_pump_model", "custom_manufacturing_date",
			"custom_qc_status", "warehouse", "custom_dealer", "custom_registration"],
		order_by="custom_manufacturing_date asc",
		limit=20000)

	# where did the ones that are no longer in stock actually go
	gone = [s.name for s in serials if not s.warehouse and not s.custom_registration]
	shipped = {}
	if gone:
		for row in frappe.db.sql("""
			select sbe.serial_no, sbb.voucher_type, sbb.voucher_no, sbb.posting_datetime
			from `tabSerial and Batch Entry` sbe
			join `tabSerial and Batch Bundle` sbb on sbb.name = sbe.parent
			where sbb.docstatus = 1
			  and ifnull(sbb.is_cancelled, 0) = 0
			  and sbb.type_of_transaction = 'Outward'
			  and sbb.voucher_type in ('Delivery Note', 'Sales Invoice')
			  and sbe.serial_no in %(serials)s
			order by sbb.posting_datetime asc
		""", {"serials": gone}, as_dict=True):
			shipped[row.serial_no] = row

	notes = [r for r in shipped.values() if r.voucher_type == "Delivery Note"]
	customers = {}
	if notes:
		for dn in frappe.get_all("Delivery Note",
				filters={"name": ["in", [r.voucher_no for r in notes]]},
				fields=["name", "customer_name", "custom_dealer"]):
			customers[dn.name] = dn

	today = frappe.utils.getdate(frappe.utils.nowdate())
	rows = []
	for s in serials:
		built = s.custom_manufacturing_date
		age = frappe.utils.date_diff(today, built) if built else 0

		ship = shipped.get(s.name)
		dn = customers.get(ship.voucher_no) if ship else None
		dealer = s.custom_dealer or (dn.custom_dealer if dn else None)

		if s.custom_registration:
			verdict = DONE
			action = ""
		elif s.warehouse and (s.custom_qc_status or "") != "Passed":
			verdict = HELD
			action = "Finish the test certificate before this can be dispatched"
		elif s.warehouse:
			verdict = STOCK
			action = ""
		elif ship:
			# it left the building on a real document and nobody registered it,
			# so its warranty never started
			verdict = GAP
			if dealer:
				action = "Ask " + dealer + " for the invoice and customer, then register it"
			else:
				action = "Went out on " + ship.voucher_no + " - get the sale details and register it"
		else:
			# not in a warehouse and never issued on any document either: the
			# serial exists but no stock movement was ever posted for it
			verdict = ORPHAN
			action = "Not in stock and never issued - post the opening stock, or delete it"

		rows.append({
			# rank rides along so the sort key needs no closure - a lambda inside
			# safe_exec cannot see names defined in the script's own scope
			"rank": {GAP: 0, ORPHAN: 1, HELD: 2, STOCK: 3, DONE: 4}.get(verdict, 9),
			"verdict": verdict,
			"serial_no": s.name,
			"model": s.custom_pump_model,
			"item_code": s.item_code,
			"manufactured": built,
			"age_days": age,
			"qc": s.custom_qc_status,
			"warehouse": s.warehouse,
			"shipped_on": frappe.utils.getdate(ship.posting_datetime) if ship else None,
			"shipped_via": ship.voucher_no if ship else None,
			"voucher_type": ship.voucher_type if ship else None,
			"billed_to": dn.customer_name if dn else None,
			"dealer": dealer,
			"action": action,
		})

	if filters.get("verdict"):
		rows = [r for r in rows if r["verdict"] == filters.get("verdict")]
	elif not filters.get("include_settled"):
		# by default show only what somebody still has to do something about
		rows = [r for r in rows if r["verdict"] != DONE]

	rows.sort(key=lambda r: (r["rank"], -(r["age_days"] or 0)))

	summary = {}
	for r in rows:
		summary[r["verdict"]] = summary.get(r["verdict"], 0) + 1

	message = "  |  ".join([k + ": " + str(v) for k, v in sorted(summary.items())])
	return columns, rows, message

