"""Scheduled jobs: keep warranty status, SLA flags and batch alerts current."""

import frappe
from frappe.utils import add_days, cint, flt, now_datetime, nowdate

from kumar_service.utils import setting


def update_warranty_status():
	"""Nightly: In Warranty -> Expiring Soon -> Expired without anyone touching it."""
	today = nowdate()
	soon = add_days(today, 30)

	frappe.db.sql(
		"""
		update `tabSerial No`
		set custom_warranty_status = 'Expired'
		where custom_registration is not null
		  and custom_warranty_expiry_date is not null
		  and custom_warranty_expiry_date < %s
		  and ifnull(custom_warranty_status, '') not in ('Expired', 'Void')
		""",
		(today,),
	)
	frappe.db.sql(
		"""
		update `tabSerial No`
		set custom_warranty_status = 'Expiring Soon'
		where custom_registration is not null
		  and custom_warranty_expiry_date between %s and %s
		  and ifnull(custom_warranty_status, '') not in ('Expiring Soon', 'Void')
		""",
		(today, soon),
	)
	frappe.db.sql(
		"""
		update `tabSerial No`
		set custom_warranty_status = 'In Warranty'
		where custom_registration is not null
		  and custom_warranty_expiry_date > %s
		  and ifnull(custom_warranty_status, '') not in ('In Warranty', 'Void')
		""",
		(soon,),
	)
	frappe.db.commit()


def send_expiry_reminders():
	"""Notify the dealer before a customer's warranty lapses."""
	days_list = [cint(d) for d in str(setting("warranty_reminder_days", "30,7")).split(",") if d.strip()]
	for days in days_list:
		target = add_days(nowdate(), days)
		rows = frappe.get_all(
			"Serial No",
			filters={"custom_warranty_expiry_date": target, "custom_registration": ["is", "set"]},
			fields=["name", "custom_dealer", "custom_end_customer_name", "custom_end_customer_mobile"],
			limit=500,
		)
		for row in rows:
			owner = frappe.db.get_value("Dealer", row.custom_dealer, "portal_user")
			if not owner:
				continue
			frappe.get_doc(
				{
					"doctype": "Notification Log",
					"subject": f"Warranty expiring in {days} days: {row.name}",
					"email_content": (
						f"Pump {row.name} sold to {row.custom_end_customer_name} "
						f"({row.custom_end_customer_mobile}) goes out of warranty on {target}."
					),
					"for_user": owner,
					"type": "Alert",
					"document_type": "Serial No",
					"document_name": row.name,
				}
			).insert(ignore_permissions=True)
	frappe.db.commit()


def flag_sla_breaches():
	"""Mark requests that blew their response or resolution window."""
	now = now_datetime()
	breached = frappe.get_all(
		"Service Request",
		filters={
			"docstatus": ["<", 2],
			"status": ["not in", ["Resolved", "Closed", "Cancelled"]],
			"resolution_due_on": ["<", now],
			"sla_status": ["!=", "Failed"],
		},
		pluck="name",
	)
	for name in breached:
		frappe.db.set_value("Service Request", name, "sla_status", "Failed", update_modified=False)

	if breached:
		managers = frappe.get_all(
			"Has Role", filters={"role": "Service Manager", "parenttype": "User"}, pluck="parent"
		)
		for user in set(managers):
			frappe.get_doc(
				{
					"doctype": "Notification Log",
					"subject": f"{len(breached)} service request(s) breached SLA",
					"email_content": "Breached: " + ", ".join(breached[:20]),
					"for_user": user,
					"type": "Alert",
				}
			).insert(ignore_permissions=True)
	frappe.db.commit()


def batch_failure_scan():
	"""Weekly: shout about any heat/winding batch failing above the threshold."""
	from kumar_service.traceability import trace_forward

	threshold = flt(setting("batch_failure_threshold_pct", 5))
	batches = frappe.get_all(
		"Batch",
		filters={"custom_batch_type": ["in", ["Heat", "Winding"]]},
		pluck="name",
		limit=500,
	)

	flagged = []
	for batch in batches:
		result = trace_forward(batch)
		if result["total_units"] >= 5 and result["failure_rate_pct"] > threshold:
			flagged.append((batch, result["failure_rate_pct"], result["total_units"]))

	if not flagged:
		return

	engineers = frappe.get_all(
		"Has Role", filters={"role": "Quality Engineer", "parenttype": "User"}, pluck="parent"
	)
	body = "".join(
		f"<li>{b}: {rate}% failure across {units} units</li>" for b, rate, units in flagged
	)
	for user in set(engineers):
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": f"{len(flagged)} batch(es) above the failure threshold",
				"email_content": f"<ul>{body}</ul>",
				"for_user": user,
				"type": "Alert",
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()
