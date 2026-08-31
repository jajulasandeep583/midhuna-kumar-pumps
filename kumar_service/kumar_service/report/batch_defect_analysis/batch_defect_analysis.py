"""Batch Defect Analysis.

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
	return columns, rows

