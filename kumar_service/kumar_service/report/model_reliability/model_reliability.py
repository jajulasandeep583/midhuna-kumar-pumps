"""Model Reliability.

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
	return columns, rows

