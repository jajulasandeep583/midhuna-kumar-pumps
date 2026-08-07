"""Warranty claim workflow: Draft -> Pending Review -> Under Investigation -> Approved/Rejected -> Settled."""

import frappe

WORKFLOW = "Kumar Warranty Claim Approval"

STATES = [
	# state, doc_status, allow_edit, style
	("Draft", 0, "Dealer", ""),
	("Pending Review", 1, "Service Manager", "Warning"),
	("Under Investigation", 1, "Quality Engineer", "Warning"),
	("Approved", 1, "Warranty Approver", "Success"),
	("Rejected", 1, "Warranty Approver", "Danger"),
	("Settled", 1, "Accounts User", "Success"),
]

TRANSITIONS = [
	# state, action, next_state, allowed role
	("Draft", "Submit for Review", "Pending Review", "Dealer"),
	("Pending Review", "Review", "Under Investigation", "Service Manager"),
	("Pending Review", "Reject", "Rejected", "Service Manager"),
	("Under Investigation", "Approve", "Approved", "Quality Engineer"),
	("Under Investigation", "Reject", "Rejected", "Quality Engineer"),
	("Approved", "Settle", "Settled", "Accounts User"),
]


def build_all():
	for state, _ds, _edit, style in STATES:
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc(
				{"doctype": "Workflow State", "workflow_state_name": state, "style": style}
			).insert(ignore_permissions=True)

	for _s, action, *_rest in TRANSITIONS:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc(
				{"doctype": "Workflow Action Master", "workflow_action_name": action}
			).insert(ignore_permissions=True)

	doc = (
		frappe.get_doc("Workflow", WORKFLOW)
		if frappe.db.exists("Workflow", WORKFLOW)
		else frappe.new_doc("Workflow")
	)
	doc.update(
		{
			"workflow_name": WORKFLOW,
			"document_type": "Kumar Warranty Claim",
			"workflow_state_field": "workflow_state",
			"is_active": 1,
			"send_email_alert": 0,
			"override_status": 0,
		}
	)
	doc.set("states", [])
	for state, docstatus, allow_edit, _style in STATES:
		doc.append("states", {"state": state, "doc_status": docstatus, "allow_edit": allow_edit})

	doc.set("transitions", [])
	for state, action, next_state, role in TRANSITIONS:
		doc.append(
			"transitions",
			{
				"state": state,
				"action": action,
				"next_state": next_state,
				"allowed": role,
				"allow_self_approval": 1,
			},
		)

	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True) if doc.name else doc.insert(ignore_permissions=True)
	frappe.db.commit()
