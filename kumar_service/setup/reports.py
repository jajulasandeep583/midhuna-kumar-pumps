"""Reports, created as DocType records so they ship with the app.

Query reports for the straightforward lists; script reports where the answer
needs real logic (failure rates, genealogy, cost roll-ups).
"""

import frappe

MODULE = "Kumar Service"


def _filters_js(filters):
	"""Client script that gives a script report its filter bar."""
	if not filters:
		return ""
	return (
		"frappe.query_reports[%s] = {\n\t\"filters\": %s\n};"
		% (frappe.as_json(_FILTER_REPORT_NAME[0]), frappe.as_json(filters))
	)


_FILTER_REPORT_NAME = [""]


def _report(name, ref_doctype, report_type, *, query=None, script=None, roles=None,
		add_total_row=0, prepared=0, filters=None):
	doc = (
		frappe.get_doc("Report", name)
		if frappe.db.exists("Report", name)
		else frappe.new_doc("Report")
	)
	doc.update(
		{
			"report_name": name,
			"ref_doctype": ref_doctype,
			"report_type": report_type,
			"module": MODULE,
			"is_standard": "No",
			"disabled": 0,
			"add_total_row": add_total_row,
			"prepared_report": prepared,
			"query": query or "",
			"report_script": script or "",
		}
	)
	_FILTER_REPORT_NAME[0] = name
	doc.javascript = _filters_js(filters)
	doc.set("roles", [])
	for role in roles or ["System Manager"]:
		if frappe.db.exists("Role", role):
			doc.append("roles", {"role": role})
	doc.flags.ignore_permissions = True
	if doc.get("__islocal") or not frappe.db.exists("Report", name):
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)
	return doc.name


WARRANTY_EXPIRING = """
select
	sn.name as "Serial No:Link/Serial No:180",
	sn.custom_pump_model as "Model:Link/Pump Model:150",
	sn.custom_dealer as "Dealer:Link/Dealer:220",
	sn.custom_end_customer_name as "Customer:Data:150",
	sn.custom_end_customer_mobile as "Mobile:Data:110",
	sn.custom_sale_date as "Sold On:Date:100",
	sn.custom_warranty_expiry_date as "Expires:Date:100",
	datediff(sn.custom_warranty_expiry_date, curdate()) as "Days Left:Int:90",
	sn.custom_warranty_status as "Status:Data:120"
from `tabSerial No` sn
where sn.custom_registration is not null
  and sn.custom_warranty_expiry_date between curdate() and date_add(curdate(), interval 30 day)
order by sn.custom_warranty_expiry_date asc
"""

UNREGISTERED_STOCK = """
select
	sn.name as "Serial No:Link/Serial No:180",
	sn.item_code as "Item:Link/Item:180",
	sn.custom_pump_model as "Model:Link/Pump Model:150",
	sn.custom_manufacturing_date as "Manufactured:Date:110",
	datediff(curdate(), sn.custom_manufacturing_date) as "Age (Days):Int:90",
	sn.custom_qc_status as "QC:Data:90",
	sn.custom_dealer as "Dealer:Link/Dealer:200",
	sn.warehouse as "Warehouse:Link/Warehouse:160"
from `tabSerial No` sn
where sn.custom_registration is null
  and ifnull(sn.custom_qc_status, '') = 'Passed'
order by sn.custom_manufacturing_date asc
"""

SLA_COMPLIANCE = """
select
	sr.name as "Request:Link/Service Request:130",
	sr.serial_no as "Serial No:Link/Serial No:170",
	sr.complaint_category as "Complaint:Data:140",
	sr.priority as "Priority:Data:80",
	sr.assigned_technician as "Technician:Link/Service Technician:140",
	sr.service_centre as "Service Centre:Link/Dealer:180",
	sr.reported_on as "Reported:Datetime:150",
	sr.first_response_on as "First Response:Datetime:150",
	sr.resolved_on as "Resolved:Datetime:150",
	sr.sla_status as "SLA:Data:100",
	case when sr.first_response_on is null then null
		 else round(timestampdiff(minute, sr.reported_on, sr.first_response_on)/60, 1) end
		 as "Response Hrs:Float:110",
	case when sr.resolved_on is null then null
		 else round(timestampdiff(minute, sr.reported_on, sr.resolved_on)/60, 1) end
		 as "Resolution Hrs:Float:120"
from `tabService Request` sr
where sr.docstatus < 2
order by sr.reported_on desc
"""

HEAT_CHEMISTRY = """
select
	hr.heat_no as "Heat No:Data:130",
	hr.heat_date as "Date:Date:100",
	hr.target_grade as "Target Grade:Data:110",
	hr.carbon_equivalent as "CE:Float:70",
	hsr.element as "Element:Data:80",
	hsr.value_pct as "Value %%:Float:90",
	hsr.spec_min as "Min:Float:70",
	hsr.spec_max as "Max:Float:70",
	case when hsr.within_spec = 1 then 'OK' else 'OUT OF SPEC' end as "Result:Data:110",
	hr.status as "Status:Data:150"
from `tabHeat Record` hr
inner join `tabHeat Spectro Reading` hsr on hsr.parent = hr.name
order by hr.heat_date desc, hr.heat_no, hsr.element
"""

TECHNICIAN_PRODUCTIVITY = """
select
	sv.technician as "Technician:Link/Service Technician:170",
	count(distinct sv.name) as "Visits:Int:80",
	count(distinct sv.service_request) as "Requests Attended:Int:140",
	round(avg(sv.customer_rating), 2) as "Avg Rating:Float:100",
	sum(sv.grand_total) as "Billed Value:Currency:130",
	sum(case when sv.is_chargeable = 0 then 1 else 0 end) as "Warranty Jobs:Int:120"
from `tabService Visit` sv
where sv.docstatus = 1
group by sv.technician
order by count(distinct sv.name) desc
"""

# NOTE: script reports run inside safe_exec - no imports, and no augmented
# assignment into dict items. Both rules are why these read a little long-hand.
BATCH_DEFECT_SCRIPT = """
columns = [
	{"label": "Batch", "fieldname": "batch", "fieldtype": "Link", "options": "Batch", "width": 150},
	{"label": "Type", "fieldname": "batch_type", "fieldtype": "Data", "width": 90},
	{"label": "Units Built", "fieldname": "units", "fieldtype": "Int", "width": 100},
	{"label": "Registered", "fieldname": "registered", "fieldtype": "Int", "width": 100},
	{"label": "With Complaints", "fieldname": "affected", "fieldtype": "Int", "width": 130},
	{"label": "Complaints", "fieldname": "complaints", "fieldtype": "Int", "width": 100},
	{"label": "Failure Rate %", "fieldname": "failure_rate", "fieldtype": "Float", "width": 130},
	{"label": "Above Threshold", "fieldname": "flag", "fieldtype": "Data", "width": 140},
	{"label": "Top Complaint", "fieldname": "top_complaint", "fieldtype": "Data", "width": 180},
]

batch_filter = {"custom_batch_type": ["in", ["Heat", "Winding"]]}
if filters.get("batch_type"):
	batch_filter["custom_batch_type"] = filters.get("batch_type")

threshold = frappe.db.get_single_value("Kumar Service Settings", "batch_failure_threshold_pct") or 5

rows = []
for b in frappe.get_all("Batch", filters=batch_filter, fields=["name", "custom_batch_type"], limit=400):
	serials = frappe.get_all("Serial No", filters={"custom_heat_no": b.name}, pluck="name")
	serials = serials + frappe.get_all("Serial No", filters={"custom_winding_batch": b.name}, pluck="name")
	serials = sorted(set(serials))
	if not serials:
		continue

	registered = frappe.db.count("Serial No",
		{"name": ["in", serials], "custom_registration": ["is", "set"]})
	reqs = frappe.get_all("Service Request",
		filters={"serial_no": ["in", serials], "docstatus": ["<", 2]},
		fields=["serial_no", "complaint_category"])

	affected = set()
	tally = {}
	for r in reqs:
		affected.add(r.serial_no)
		tally[r.complaint_category] = tally.get(r.complaint_category, 0) + 1

	rate = round(len(affected) * 100.0 / len(serials), 2)
	top = max(tally, key=tally.get) if tally else ""

	rows.append({
		"batch": b.name,
		"batch_type": b.custom_batch_type,
		"units": len(serials),
		"registered": registered,
		"affected": len(affected),
		"complaints": len(reqs),
		"failure_rate": rate,
		"flag": "YES - INVESTIGATE" if rate > threshold else "",
		"top_complaint": top,
	})

rows.sort(key=lambda r: -r["failure_rate"])
data = columns, rows
"""

SERIAL_GENEALOGY_SCRIPT = """
columns = [
	{"label": "Attribute", "fieldname": "attribute", "fieldtype": "Data", "width": 220},
	{"label": "Value", "fieldname": "value", "fieldtype": "Data", "width": 320},
]

rows = []
serial = filters.get("serial_no")
if serial:
	t = frappe.db.get_value("Serial No", serial, [
		"name", "item_code", "custom_pump_model", "custom_manufacturing_date",
		"custom_work_order", "custom_heat_no", "custom_winding_batch",
		"custom_rotor_batch", "custom_test_certificate", "custom_qc_status"], as_dict=True) or {}

	heat = {}
	if t.get("custom_heat_no"):
		heat_record = frappe.db.get_value("Batch", t.get("custom_heat_no"), "custom_heat_record")
		if heat_record:
			heat = frappe.db.get_value("Heat Record", heat_record, [
				"heat_date", "furnace", "target_grade", "grade_achieved",
				"carbon_equivalent", "all_within_spec"], as_dict=True) or {}

	wind = {}
	if t.get("custom_winding_batch"):
		wind = frappe.db.get_value("Winding Batch Record", {"batch_no": t.get("custom_winding_batch")}, [
			"winding_date", "machine", "wire_gauge_swg", "turns_per_coil",
			"ir_test_mohm", "hipot_test_kv"], as_dict=True) or {}

	cert = {}
	if t.get("custom_test_certificate"):
		cert = frappe.db.get_value("Pump Test Certificate", t.get("custom_test_certificate"), [
			"name", "test_date", "overall_result", "vibration_mm_s", "noise_db"], as_dict=True) or {}

	t["heat_batch"] = t.get("custom_heat_no")
	t["winding_batch"] = t.get("custom_winding_batch")
	t["rotor_batch"] = t.get("custom_rotor_batch")
	t["pump_model"] = t.get("custom_pump_model")
	t["manufacturing_date"] = t.get("custom_manufacturing_date")
	t["work_order"] = t.get("custom_work_order")
	t["qc_status"] = t.get("custom_qc_status")
	t["serial_no"] = t.get("name")

	pairs = [
		("Serial No", t.get("serial_no")),
		("Item", t.get("item_code")),
		("Pump Model", t.get("pump_model")),
		("Manufactured On", t.get("manufacturing_date")),
		("Work Order", t.get("work_order")),
		("QC Status", t.get("qc_status")),
		("--- Casing ---", ""),
		("Heat Batch", t.get("heat_batch")),
		("Heat Date", heat.get("heat_date")),
		("Furnace", heat.get("furnace")),
		("Target Grade", heat.get("target_grade")),
		("Grade Achieved", heat.get("grade_achieved")),
		("Carbon Equivalent", heat.get("carbon_equivalent")),
		("All Elements In Spec", "Yes" if heat.get("all_within_spec") else "No"),
		("--- Stator ---", ""),
		("Winding Batch", t.get("winding_batch")),
		("Winding Date", wind.get("winding_date")),
		("Machine", wind.get("machine")),
		("Wire Gauge (SWG)", wind.get("wire_gauge_swg")),
		("Turns per Coil", wind.get("turns_per_coil")),
		("IR Test (Mohm)", wind.get("ir_test_mohm")),
		("HiPot (kV)", wind.get("hipot_test_kv")),
		("--- Test ---", ""),
		("Test Certificate", cert.get("name")),
		("Test Date", cert.get("test_date")),
		("Overall Result", cert.get("overall_result")),
		("Vibration (mm/s)", cert.get("vibration_mm_s")),
		("Noise (dB)", cert.get("noise_db")),
	]
	for k, v in pairs:
		rows.append({"attribute": k, "value": "" if v is None else str(v)})

data = columns, rows
"""

DEALER_PERFORMANCE_SCRIPT = """
columns = [
	{"label": "Dealer", "fieldname": "dealer", "fieldtype": "Link", "options": "Dealer", "width": 240},
	{"label": "Type", "fieldname": "dealer_type", "fieldtype": "Data", "width": 150},
	{"label": "State", "fieldname": "state", "fieldtype": "Data", "width": 130},
	{"label": "Registrations", "fieldname": "registrations", "fieldtype": "Int", "width": 120},
	{"label": "Complaints", "fieldname": "complaints", "fieldtype": "Int", "width": 100},
	{"label": "Complaint Rate %", "fieldname": "rate", "fieldtype": "Float", "width": 140},
	{"label": "Claims", "fieldname": "claims", "fieldtype": "Int", "width": 80},
	{"label": "Claim Value", "fieldname": "claim_value", "fieldtype": "Currency", "width": 130},
]

dealer_filter = {"is_group": 0}
if filters.get("dealer_type"):
	dealer_filter["dealer_type"] = filters.get("dealer_type")
if filters.get("state"):
	dealer_filter["state"] = ["like", "%" + filters.get("state") + "%"]

rows = []
for d in frappe.get_all("Dealer", filters=dealer_filter, fields=["name", "dealer_type", "state"]):
	regs = frappe.db.count("Pump Registration", {"dealer": d.name, "docstatus": 1})
	comps = frappe.db.count("Service Request", {"dealer": d.name, "docstatus": ["<", 2]})
	claims = frappe.get_all("Kumar Warranty Claim",
		filters={"dealer": d.name, "docstatus": ["<", 2]}, fields=["claim_amount"])
	if not regs and not comps:
		continue
	rows.append({
		"dealer": d.name,
		"dealer_type": d.dealer_type,
		"state": d.state,
		"registrations": regs,
		"complaints": comps,
		"rate": round(comps * 100.0 / regs, 2) if regs else 0,
		"claims": len(claims),
		"claim_value": sum(c.claim_amount or 0 for c in claims),
	})

rows.sort(key=lambda r: -r["registrations"])
data = columns, rows
"""

MODEL_RELIABILITY_SCRIPT = """
columns = [
	{"label": "Pump Model", "fieldname": "model", "fieldtype": "Link", "options": "Pump Model", "width": 200},
	{"label": "Category", "fieldname": "category", "fieldtype": "Data", "width": 180},
	{"label": "HP", "fieldname": "hp", "fieldtype": "Float", "width": 70},
	{"label": "Units Sold", "fieldname": "sold", "fieldtype": "Int", "width": 100},
	{"label": "Complaints", "fieldname": "complaints", "fieldtype": "Int", "width": 100},
	{"label": "Failures per 1000", "fieldname": "per_1000", "fieldtype": "Float", "width": 150},
	{"label": "Top Complaint", "fieldname": "top", "fieldtype": "Data", "width": 180},
]

model_filter = {}
if filters.get("pump_category"):
	model_filter["pump_category"] = filters.get("pump_category")

rows = []
for m in frappe.get_all("Pump Model", filters=model_filter, fields=["name", "pump_category", "hp"], limit=200):
	sold = frappe.db.count("Pump Registration", {"pump_model": m.name, "docstatus": 1})
	if not sold:
		continue
	reqs = frappe.get_all("Service Request",
		filters={"pump_model": m.name, "docstatus": ["<", 2]}, fields=["complaint_category"])
	tally = {}
	for r in reqs:
		tally[r.complaint_category] = tally.get(r.complaint_category, 0) + 1
	top = max(tally, key=tally.get) if tally else ""
	rows.append({
		"model": m.name,
		"category": m.pump_category,
		"hp": m.hp,
		"sold": sold,
		"complaints": len(reqs),
		"per_1000": round(len(reqs) * 1000.0 / sold, 1),
		"top": top,
	})

rows.sort(key=lambda r: -r["per_1000"])
data = columns, rows
"""

WARRANTY_COST_SCRIPT = """
columns = [
	{"label": "Month", "fieldname": "month", "fieldtype": "Data", "width": 110},
	{"label": "Pump Model", "fieldname": "model", "fieldtype": "Link", "options": "Pump Model", "width": 190},
	{"label": "Root Cause", "fieldname": "root_cause", "fieldtype": "Data", "width": 180},
	{"label": "Claims", "fieldname": "claims", "fieldtype": "Int", "width": 90},
	{"label": "Claimed", "fieldname": "claimed", "fieldtype": "Currency", "width": 130},
	{"label": "Approved", "fieldname": "approved", "fieldtype": "Currency", "width": 130},
	{"label": "Status", "fieldname": "state", "fieldtype": "Data", "width": 150},
]

claim_filter = {"docstatus": ["<", 2]}
if filters.get("from_date") and filters.get("to_date"):
	claim_filter["claim_date"] = ["between", [filters.get("from_date"), filters.get("to_date")]]

bucket = {}
for c in frappe.get_all("Kumar Warranty Claim",
		filters=claim_filter,
		fields=["claim_date", "pump_model", "root_cause", "claim_amount",
			"approved_amount", "workflow_state"]):
	key = (str(c.claim_date)[:7], c.pump_model, c.root_cause or "Not Set", c.workflow_state or "Draft")
	b = bucket.setdefault(key, {"claims": 0, "claimed": 0.0, "approved": 0.0})
	# safe_exec forbids augmented assignment into dict items, so assign plainly
	b["claims"] = b["claims"] + 1
	b["claimed"] = b["claimed"] + (c.claim_amount or 0)
	b["approved"] = b["approved"] + (c.approved_amount or 0)

rows = []
for (month, model, cause, state), v in bucket.items():
	rows.append({
		"month": month, "model": model, "root_cause": cause, "state": state,
		"claims": v["claims"], "claimed": v["claimed"], "approved": v["approved"],
	})

rows.sort(key=lambda r: (r["month"], -r["claimed"]))
data = columns, rows
"""

# The data-migration reconciliation report. "Unregistered Stock" answers "what
# have we built that nobody has bought yet" - a normal, healthy number. This
# one answers the question that actually costs money: which pumps have LEFT the
# building with no registration behind them, so their warranty never started
# and a claim on them has no paperwork to stand on. After a bulk import of
# historical serials it is the list of rows that still need a home.
STOCK_RECONCILIATION_SCRIPT = """
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
	for row in frappe.db.sql(\"\"\"
		select sbe.serial_no, sbb.voucher_type, sbb.voucher_no, sbb.posting_datetime
		from `tabSerial and Batch Entry` sbe
		join `tabSerial and Batch Bundle` sbb on sbb.name = sbe.parent
		where sbb.docstatus = 1
		  and ifnull(sbb.is_cancelled, 0) = 0
		  and sbb.type_of_transaction = 'Outward'
		  and sbb.voucher_type in ('Delivery Note', 'Sales Invoice')
		  and sbe.serial_no in %(serials)s
		order by sbb.posting_datetime asc
	\"\"\", {"serials": gone}, as_dict=True):
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
data = columns, rows, message
"""


#: The company side of the dealer portal.
#:
#: A dealer raising a complaint or a claim from the portal has to be visible to
#: KUMAR staff in one place, with the same facts the dealer sees - otherwise the
#: portal is a hole that things fall into. "Raised From" is derived from the
#: document's owner: a document created by a Dealer's `portal_user` came in
#: through the portal, anything else was typed by staff at a desk.
#:
#: safe_exec rules that bite here: no imports, no augmented assignment into dict
#: items, and every literal % must be doubled.
DEALER_REQUESTS_SCRIPT = """
kind = filters.get("kind") or ""
source = filters.get("source") or ""
dealer = filters.get("dealer")
status = filters.get("status")
from_date = filters.get("from_date")
to_date = filters.get("to_date")

# safe_exec exposes get_all but NOT frappe.db.sql_list, so pluck instead.
portal_users = set(frappe.get_all(
    "Dealer", filters={"portal_user": ["!=", ""]}, pluck="portal_user"
))

scope = None
if dealer:
    bounds = frappe.db.get_value("Dealer", dealer, ["lft", "rgt"], as_dict=True)
    if bounds:
        scope = frappe.get_all(
            "Dealer",
            filters={"lft": [">=", bounds.lft], "rgt": ["<=", bounds.rgt]},
            pluck="name",
        )

rows = []
today = frappe.utils.nowdate()

if kind in ("", "Complaint"):
    for r in frappe.db.sql('''
        select sr.name, sr.dealer, sr.serial_no, sr.pump_model, sr.complaint_category,
               sr.status, sr.priority, sr.reported_on, sr.owner,
               sr.end_customer_name, sr.end_customer_mobile, sr.is_under_warranty,
               sr.sla_status, sr.resolution_due_on, sr.resolved_on,
               sr.assigned_technician, sr.linked_claim
        from   `tabService Request` sr
        where  sr.docstatus < 2
        order by sr.reported_on desc
    ''', as_dict=True):
        rows.append({
            "kind": "Complaint",
            "ref": r.name,
            "dealer": r.dealer,
            "serial_no": r.serial_no,
            "pump_model": r.pump_model,
            "detail": r.complaint_category,
            "status": r.status,
            "priority": r.priority,
            "raised_on": r.reported_on,
            "owner": r.owner,
            "customer": r.end_customer_name,
            "mobile": r.end_customer_mobile,
            "free": r.is_under_warranty,
            "sla_status": r.sla_status,
            "due_on": r.resolution_due_on,
            "closed_on": r.resolved_on,
            "technician": r.assigned_technician,
            "claim": r.linked_claim,
            "amount": 0,
        })

if kind in ("", "Warranty Claim"):
    for r in frappe.db.sql('''
        select wc.name, wc.dealer, wc.serial_no, wc.pump_model, wc.claim_type,
               wc.workflow_state, wc.claim_date, wc.owner, wc.claim_amount,
               wc.approved_amount, wc.settled_on, wc.service_request, wc.root_cause
        from   `tabKumar Warranty Claim` wc
        where  wc.docstatus < 2
        order by wc.claim_date desc
    ''', as_dict=True):
        rows.append({
            "kind": "Warranty Claim",
            "ref": r.name,
            "dealer": r.dealer,
            "serial_no": r.serial_no,
            "pump_model": r.pump_model,
            "detail": r.claim_type,
            "status": r.workflow_state or "Draft",
            "priority": "",
            "raised_on": r.claim_date,
            "owner": r.owner,
            "customer": "",
            "mobile": "",
            "free": 0,
            "sla_status": r.root_cause,
            "due_on": None,
            "closed_on": r.settled_on,
            "technician": "",
            "claim": r.service_request,
            "amount": r.claim_amount or 0,
        })

out = []
for row in rows:
    row["raised_from"] = "Portal" if row["owner"] in portal_users else "Desk"
    if source and row["raised_from"] != source:
        continue
    if scope is not None and row["dealer"] not in scope:
        continue
    if status and row["status"] != status:
        continue
    stamp = frappe.utils.get_datetime_str(row["raised_on"]) if row["raised_on"] else ""
    day = stamp[:10] if stamp else ""
    if from_date and day and day < str(from_date):
        continue
    if to_date and day and day > str(to_date):
        continue

    closed = row["closed_on"]
    end = frappe.utils.get_datetime_str(closed)[:10] if closed else today
    row["age_days"] = frappe.utils.date_diff(end, day) if day else 0
    row["is_open"] = 0 if closed else 1

    # Late means: still open and past the promised date. Computed here rather
    # than trusted from sla_status, which only moves when someone touches the doc.
    late = 0
    if row["due_on"] and not closed:
        if frappe.utils.get_datetime_str(row["due_on"]) < frappe.utils.now():
            late = 1
    row["late"] = late
    out.append(row)

out.sort(key=lambda r: (0 if r["is_open"] else 1, -1 * (r["late"] or 0),
                        str(r["raised_on"] or "")), reverse=False)

columns = [
    {"label": "Type", "fieldname": "kind", "fieldtype": "Data", "width": 110},
    {"label": "Reference", "fieldname": "ref", "fieldtype": "Dynamic Link",
     "options": "doctype_for_ref", "width": 130},
    {"label": "Raised From", "fieldname": "raised_from", "fieldtype": "Data", "width": 95},
    {"label": "Dealer", "fieldname": "dealer", "fieldtype": "Link", "options": "Dealer", "width": 210},
    {"label": "Serial No", "fieldname": "serial_no", "fieldtype": "Link",
     "options": "Serial No", "width": 200},
    {"label": "Model", "fieldname": "pump_model", "fieldtype": "Link",
     "options": "Pump Model", "width": 150},
    {"label": "Detail", "fieldname": "detail", "fieldtype": "Data", "width": 150},
    {"label": "Customer", "fieldname": "customer", "fieldtype": "Data", "width": 160},
    {"label": "Mobile", "fieldname": "mobile", "fieldtype": "Data", "width": 110},
    {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 130},
    {"label": "Late", "fieldname": "late", "fieldtype": "Check", "width": 60},
    {"label": "Open", "fieldname": "is_open", "fieldtype": "Check", "width": 60},
    {"label": "Age (days)", "fieldname": "age_days", "fieldtype": "Int", "width": 90},
    {"label": "Raised On", "fieldname": "raised_on", "fieldtype": "Datetime", "width": 140},
    {"label": "Claim Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
    {"label": "Technician", "fieldname": "technician", "fieldtype": "Data", "width": 140},
    {"label": "Linked", "fieldname": "claim", "fieldtype": "Data", "width": 130},
]

for row in out:
    row["doctype_for_ref"] = (
        "Service Request" if row["kind"] == "Complaint" else "Kumar Warranty Claim"
    )

# `data`, not `result`: Report.execute_script only honours the script's own
# columns when `data` is set. Setting `result` makes frappe fall back to
# get_columns() off the Report's (empty) child table, and every column vanishes.
data = columns, out
"""


def build_all():
	_report("Warranty Expiring Soon", "Serial No", "Query Report", query=WARRANTY_EXPIRING,
		roles=["System Manager", "Warranty Approver", "Service Manager", "Dealer Manager", "Dealer"])
	_report("Unregistered Stock", "Serial No", "Query Report", query=UNREGISTERED_STOCK,
		roles=["System Manager", "Warranty Approver", "Service Manager", "Production Manager"])
	_report("SLA Compliance", "Service Request", "Query Report", query=SLA_COMPLIANCE,
		roles=["System Manager", "Service Manager"])
	_report("Heat Chemistry Log", "Heat Record", "Query Report", query=HEAT_CHEMISTRY,
		roles=["System Manager", "Quality Engineer", "Production Manager"])
	_report("Technician Productivity", "Service Visit", "Query Report", query=TECHNICIAN_PRODUCTIVITY,
		roles=["System Manager", "Service Manager"])

	_report("Batch Defect Analysis", "Serial No", "Script Report", script=BATCH_DEFECT_SCRIPT,
		roles=["System Manager", "Quality Engineer", "Warranty Approver", "Production Manager"],
		filters=[
			{"fieldname": "batch_type", "label": "Batch Type", "fieldtype": "Select",
				"options": "\nHeat\nWinding", "default": ""},
		])
	_report("Serial Genealogy", "Serial No", "Script Report", script=SERIAL_GENEALOGY_SCRIPT,
		roles=["System Manager", "Quality Engineer", "Service Manager", "Production Manager"],
		filters=[
			{"fieldname": "serial_no", "label": "Serial No", "fieldtype": "Link",
				"options": "Serial No", "reqd": 1},
		])
	_report("Dealer Performance", "Pump Registration", "Script Report", script=DEALER_PERFORMANCE_SCRIPT,
		roles=["System Manager", "Dealer Manager", "Service Manager"],
		filters=[
			{"fieldname": "dealer_type", "label": "Dealer Type", "fieldtype": "Select",
				"options": "\nBranch Office\nAuthorised Distributor\nDealer\nSub-Dealer\nService Centre"},
			{"fieldname": "state", "label": "State", "fieldtype": "Data"},
		])
	_report("Model Reliability", "Pump Registration", "Script Report", script=MODEL_RELIABILITY_SCRIPT,
		roles=["System Manager", "Quality Engineer", "Production Manager", "Service Manager"],
		filters=[
			{"fieldname": "pump_category", "label": "Pump Category", "fieldtype": "Link",
				"options": "Pump Category"},
		])
	_report("Stock vs Registration Reconciliation", "Serial No", "Script Report",
		script=STOCK_RECONCILIATION_SCRIPT,
		roles=["System Manager", "Warranty Approver", "Service Manager", "Dealer Manager",
			"Production Manager"],
		filters=[
			{"fieldname": "verdict", "label": "Verdict", "fieldtype": "Select",
				"options": "\nSHIPPED - NOT REGISTERED\nNo stock record at all\n"
					"Held - QC not passed\nIn stock - not sold yet\nRegistered"},
			{"fieldname": "pump_model", "label": "Pump Model", "fieldtype": "Link",
				"options": "Pump Model"},
			{"fieldname": "item_code", "label": "Item", "fieldtype": "Link", "options": "Item"},
			{"fieldname": "from_date", "label": "Built From", "fieldtype": "Date"},
			{"fieldname": "to_date", "label": "Built To", "fieldtype": "Date"},
			{"fieldname": "include_settled", "label": "Include Already Registered",
				"fieldtype": "Check", "default": 0},
		])
	_report("Warranty Cost Analysis", "Kumar Warranty Claim", "Script Report", script=WARRANTY_COST_SCRIPT,
		roles=["System Manager", "Warranty Approver", "Accounts User"],
		filters=[
			{"fieldname": "from_date", "label": "From Date", "fieldtype": "Date",
				"default": "frappe.datetime.add_months(frappe.datetime.get_today(), -3)"},
			{"fieldname": "to_date", "label": "To Date", "fieldtype": "Date",
				"default": "frappe.datetime.get_today()"},
		])

	_report("Dealer Requests & Claims", "Service Request", "Script Report",
		script=DEALER_REQUESTS_SCRIPT,
		roles=["System Manager", "Service Manager", "Warranty Approver", "Dealer Manager"],
		filters=[
			{"fieldname": "kind", "label": "Type", "fieldtype": "Select",
				"options": "\nComplaint\nWarranty Claim"},
			{"fieldname": "source", "label": "Raised From", "fieldtype": "Select",
				"options": "\nPortal\nDesk"},
			{"fieldname": "dealer", "label": "Dealer (with its network)", "fieldtype": "Link",
				"options": "Dealer"},
			{"fieldname": "status", "label": "Status", "fieldtype": "Data"},
			{"fieldname": "from_date", "label": "Raised From Date", "fieldtype": "Date",
				"default": "frappe.datetime.add_months(frappe.datetime.get_today(), -3)"},
			{"fieldname": "to_date", "label": "Raised To Date", "fieldtype": "Date",
				"default": "frappe.datetime.get_today()"},
		])

	frappe.db.commit()
