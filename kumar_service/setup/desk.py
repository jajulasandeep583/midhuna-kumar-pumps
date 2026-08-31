"""KUMAR Pumps Desk - the helpdesk agent workspace, set up from code.

The desk itself is frappe/helpdesk, forked into this bench. Everything that
makes it KUMAR's rather than a stock install lives here rather than in somebody's
memory of which buttons they clicked: the brand, who counts as an agent, and the
ticket types that match how a pump actually fails.

Kept in kumar_service, not in the fork, on purpose. The fork should stay as close
to upstream as it can so its fixes can still be pulled; anything specific to
KUMAR belongs on our side of the line.
"""

import frappe

BRAND = "KUMAR Pumps Desk"

# Who answers dealers. These are the same roles the Service Request desk already
# treats as staff, so nobody has to be granted a second, parallel kind of access.
AGENT_ROLES = (
	"Service Manager",
	"Warranty Approver",
	"Quality Engineer",
	"Dealer Manager",
)

# A pump does not fail in the abstract; it fails in one of these ways, and the
# desk should offer the same vocabulary the Service Request already uses.
TICKET_TYPES = (
	"Complaint",
	"Warranty Claim",
	"Installation",
	"Spare Part",
	"Enquiry",
)


def brand():
	"""Name the product KUMAR Pumps Desk wherever the agent UI shows a name."""
	if not frappe.db.exists("DocType", "HD Settings"):
		return None
	s = frappe.get_single("HD Settings")
	changed = False
	if s.meta.has_field("brand_name") and s.brand_name != BRAND:
		s.brand_name = BRAND
		changed = True
	# stop the stock first-run wizard nagging on a desk we configured from code
	for flag in ("setup_complete", "initial_helpdesk_name_setup_skipped"):
		if s.meta.has_field(flag) and not s.get(flag):
			s.set(flag, 1)
			changed = True
	if changed:
		s.flags.ignore_permissions = True
		s.save(ignore_permissions=True)
	return BRAND


def agents():
	"""Every KUMAR staff login becomes an agent; dealers never do.

	A dealer reaches the desk through the portal, which is the whole point of
	having a portal. Making one an agent would hand them the queue.
	"""
	if not frappe.db.exists("DocType", "HD Agent"):
		return []

	users = set()
	for role in AGENT_ROLES:
		users.update(
			frappe.get_all(
				"Has Role",
				filters={"role": role, "parenttype": "User"},
				pluck="parent",
			)
		)
	# a dealer login is never an agent, whatever else it happens to hold
	dealer_users = set(
		frappe.get_all("Dealer", pluck="portal_user", limit_page_length=0)
	) - {None, ""}
	users -= dealer_users
	users.discard("Guest")

	made = []
	for user in sorted(users):
		if not frappe.db.exists("User", user):
			continue
		if frappe.db.exists("HD Agent", {"user": user}):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "HD Agent",
				"user": user,
				"agent_name": frappe.db.get_value("User", user, "full_name") or user,
				"is_active": 1,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		made.append(user)
	return made


def ticket_types():
	if not frappe.db.exists("DocType", "HD Ticket Type"):
		return []
	made = []
	for name in TICKET_TYPES:
		if frappe.db.exists("HD Ticket Type", name):
			continue
		doc = frappe.get_doc({"doctype": "HD Ticket Type", "name": name})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		made.append(name)
	return made


def build_all():
	if not frappe.db.exists("DocType", "HD Settings"):
		frappe.msgprint("helpdesk is not installed on this site; skipping the desk setup")
		return
	out = {"brand": brand(), "agents": agents(), "ticket_types": ticket_types()}
	frappe.db.commit()
	return out
