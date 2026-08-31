"""Warranty Cost Analysis.

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
	return columns, rows

