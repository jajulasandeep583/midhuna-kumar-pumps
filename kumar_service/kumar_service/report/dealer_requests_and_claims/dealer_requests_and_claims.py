"""Dealer Requests and Claims.

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
	return columns, out

