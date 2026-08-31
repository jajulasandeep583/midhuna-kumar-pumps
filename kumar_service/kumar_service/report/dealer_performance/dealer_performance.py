"""Dealer Performance.

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
	return columns, rows

