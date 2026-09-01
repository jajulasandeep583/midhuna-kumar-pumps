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


# What HD Ticket has to carry to be a useful mirror of a Service Request. These
# are custom fields on the fork's doctype rather than edits to its json, so the
# fork stays mergeable with upstream.
TICKET_FIELDS = [
	{
		"fieldname": "custom_kumar_section",
		"fieldtype": "Section Break",
		"label": "KUMAR Pump",
		"insert_after": "description",
	},
	{
		"fieldname": "custom_service_request",
		"fieldtype": "Link",
		"options": "Service Request",
		"label": "Service Request",
		"read_only": 1,
		"in_standard_filter": 1,
		"insert_after": "custom_kumar_section",
		"description": "The request this ticket mirrors. That document, not this one, is the record.",
	},
	{
		"fieldname": "custom_serial_no",
		"fieldtype": "Link",
		"options": "Serial No",
		"label": "Serial No",
		"read_only": 1,
		"in_standard_filter": 1,
		"insert_after": "custom_service_request",
	},
	{
		"fieldname": "custom_pump_model",
		"fieldtype": "Data",
		"label": "Pump Model",
		"read_only": 1,
		"insert_after": "custom_serial_no",
	},
	{
		"fieldname": "custom_kumar_col",
		"fieldtype": "Column Break",
		"insert_after": "custom_pump_model",
	},
	{
		"fieldname": "custom_dealer",
		"fieldtype": "Link",
		"options": "Dealer",
		"label": "Dealer",
		"read_only": 1,
		"in_standard_filter": 1,
		"insert_after": "custom_kumar_col",
	},
	{
		"fieldname": "custom_warranty",
		"fieldtype": "Data",
		"label": "Warranty",
		"read_only": 1,
		"in_standard_filter": 1,
		"insert_after": "custom_dealer",
		"description": "Whether the visit is chargeable - the first thing a dealer asks.",
	},
]


# Not every service need is a complaint. A dealer ringing about an installation,
# a paid visit or a spare part was previously forced to file all of it as a
# complaint, which made "complaints per model" a meaningless number and told the
# service desk nothing about what was actually being asked for.
#
# One field on the request rather than a second form: two forms writing the same
# doctype is how a dealer ends up guessing which one to use.
REQUEST_TYPES = [
	"Complaint",
	"Installation",
	"Paid Service",
	"Spare Part",
	"Enquiry",
]

SERVICE_REQUEST_FIELDS = [
	{
		"fieldname": "custom_request_type",
		"fieldtype": "Select",
		"label": "Request Type",
		"options": "\n".join(REQUEST_TYPES),
		"default": "Complaint",
		"insert_after": "complaint_category",
		"in_standard_filter": 1,
		"description": "What the dealer is asking for. A complaint is a fault; "
		"the rest are work they want done.",
	}
]


def request_type_field():
	if not frappe.db.exists("DocType", "Service Request"):
		return []
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Service Request": SERVICE_REQUEST_FIELDS}, ignore_validate=True,
		update=True)
	return [f["fieldname"] for f in SERVICE_REQUEST_FIELDS]


def ticket_fields():
	"""Put the pump facts on HD Ticket, as custom fields."""
	if not frappe.db.exists("DocType", "HD Ticket"):
		return []
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"HD Ticket": TICKET_FIELDS}, ignore_validate=True, update=True)
	return [f["fieldname"] for f in TICKET_FIELDS]


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


# ---------------------------------------------------------------- dealers

# Doctypes a dealer must be able to READ for the desk pages to work at all.
# Each one is already row-scoped by a permission_query_conditions entry and a
# has_permission hook in kumar_service.permissions, so granting the role read
# widens which doctypes they may touch, never which rows.
DEALER_READ = ("Serial No",)

# The same doctype, for the people answering the dealer. A service manager on
# the phone needs to check a serial - which pump, whose, still in warranty - and
# could not: Serial No read belonged to the stock roles and nobody else, so the
# lookup failed for the very people whose job is answering that question.
# has_full_access already covers these roles at document level; this is only the
# doctype permission that was never granted.
STAFF_READ_ROLES = ("Service Manager", "Warranty Approver", "Quality Engineer",
	"Dealer Manager", "Service Technician")


def staff_permissions():
	from frappe.permissions import add_permission, update_permission_property

	granted = []
	for doctype in ("Serial No",):
		if not frappe.db.exists("DocType", doctype):
			continue
		for role in STAFF_READ_ROLES:
			if not frappe.db.exists("Role", role):
				continue
			if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}) or \
				frappe.db.exists("DocPerm", {"parent": doctype, "role": role}):
				continue
			add_permission(doctype, role, 0)
			for prop in ("write", "create", "delete", "submit", "cancel", "amend"):
				update_permission_property(doctype, role, 0, prop, 0)
			# `report` is a separate permission from `read`, and a report query
			# checks it specifically - so granting read alone left Serial
			# Genealogy and the stock reconciliation failing with "you don't have
			# permission to get a report on: Serial No" for the very roles the
			# reports are addressed to. Rows stay scoped either way: a report
			# query honours permission_query_conditions like any other.
			for prop in ("report", "export"):
				update_permission_property(doctype, role, 0, prop, 1)
			granted.append(f"{doctype} -> {role}")
	if granted:
		frappe.clear_cache()
	return granted


def dealer_permissions():
	"""Grant the Dealer role read on what the desk pages actually open.

	The role could read Pump Model and Pump Category but not Serial No, so
	anything reaching a serial through the ORM - the claim page, a registration
	lookup, the REST API - failed with "does not have doctype access". The
	portal never noticed because it reads serials with frappe.db.get_value,
	which does not check permissions at all.
	"""
	from frappe.permissions import add_permission, update_permission_property

	granted = []
	for doctype in DEALER_READ:
		if not frappe.db.exists("DocType", doctype):
			continue
		if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": "Dealer"}) or \
			frappe.db.exists("DocPerm", {"parent": doctype, "role": "Dealer"}):
			continue
		add_permission(doctype, "Dealer", 0)
		# read only: a dealer never writes a serial, the plant does
		for prop in ("write", "create", "delete", "submit", "cancel", "amend"):
			update_permission_property(doctype, "Dealer", 0, prop, 0)
		granted.append(doctype)
	if granted:
		frappe.clear_cache()
	return granted


def dealers():
	"""Give every dealer login the desk as a customer, not as an agent.

	A dealer logging in saw an empty desk, and the reason is worth stating
	because it is not obvious. Helpdesk shows a non-agent only the tickets they
	own, are the contact on, or raised - plus the tickets of any HD Customer
	they are a member of. Our mirrored tickets were inserted by Administrator
	with a customer but no contact and no raiser, so a dealer matched none of
	the three and the queue came back empty.

	The chain helpdesk actually walks is
	    User -> Contact (Contact.user) -> HD Customer Member -> HD Customer
	so a dealer needs a Contact bound to their login and a membership row on
	their outlet's customer. is_manager is set, which is what lets a group
	dealer see the tickets of the whole outlet rather than only the ones they
	personally opened.

	They get the HD Customer role, never Agent: an agent sees the queue.
	"""
	if not frappe.db.exists("DocType", "HD Customer"):
		return {"linked": [], "skipped": "helpdesk is not installed"}

	from kumar_service.desk_bridge import customer_for

	linked = []
	for d in frappe.get_all(
		"Dealer", fields=["name", "portal_user", "dealer_name"], limit_page_length=0
	):
		user = d.portal_user
		if not user or not frappe.db.exists("User", user):
			continue

		customer = customer_for(d.name)
		if not customer:
			continue

		# 1. the role that opens the desk at all
		roles = set(frappe.get_roles(user))
		if "HD Customer" not in roles and frappe.db.exists("Role", "HD Customer"):
			u = frappe.get_doc("User", user)
			u.append("roles", {"role": "HD Customer"})
			u.flags.ignore_permissions = True
			u.save(ignore_permissions=True)

		# 2. the Contact that ties the login to a person
		contact = frappe.db.get_value("Contact", {"user": user})
		if not contact:
			c = frappe.get_doc(
				{
					"doctype": "Contact",
					"first_name": d.dealer_name or d.name,
					"user": user,
					"email_ids": [{"email_id": user, "is_primary": 1}],
				}
			)
			c.flags.ignore_permissions = True
			c.insert(ignore_permissions=True)
			contact = c.name

		# 3. the membership that says which outlet's tickets they may see
		# the child table is `contacts`, of HD Customer Member - not `members`
		cust = frappe.get_doc("HD Customer", customer)
		if not any(m.contact_name == contact for m in (cust.get("contacts") or [])):
			cust.append("contacts", {"contact_name": contact, "is_manager": 1})
			cust.flags.ignore_permissions = True
			cust.save(ignore_permissions=True)

		linked.append({"dealer": d.name, "user": user, "contact": contact})
	return linked


# Screens that existed only because the desk did not. Each was a workaround for
# something KUMAR Pumps Desk now does properly, and leaving them up means two
# places to look and two places to fix.
SUPERSEDED_PAGES = {
	"dealer-conversations": "the desk's Tickets queue",
	"service-command-centre": "/kumar-desk/manage",
}


def retire_superseded():
	"""Take down what the desk replaced, and helpdesk's own out-of-box furniture.

	Safe to run again: everything here checks before it deletes.
	"""
	done = []

	# helpdesk ships a sample ticket, and it sits in a real queue looking like
	# work somebody has to do
	if frappe.db.exists("DocType", "HD Ticket"):
		for t in frappe.get_all(
			"HD Ticket", filters={"custom_service_request": ["in", ["", None]]}, pluck="name"
		):
			frappe.delete_doc("HD Ticket", t, force=True, ignore_permissions=True)
			done.append(f"sample ticket {t}")

	# helpdesk ships a placeholder article called "Introduction", in Draft, in a
	# category called General. It is the first thing anyone sees in a Knowledge
	# Base that now has real articles in it.
	if frappe.db.exists("DocType", "HD Article"):
		# HD Article Category refuses to lose its last article, so the order
		# matters: move the placeholder into a category that has others, delete
		# it there, and only then take the empty category away.
		host = frappe.db.get_value(
			"HD Article Category", {"category_name": "Before you call KUMAR"}
		)
		for a in frappe.get_all(
			"HD Article", filters={"title": "Introduction", "status": "Draft"},
			fields=["name", "category"],
		):
			old_category = a.category
			if host and old_category != host:
				frappe.db.set_value("HD Article", a.name, "category", host)
			frappe.delete_doc("HD Article", a.name, force=True, ignore_permissions=True)
			done.append("placeholder article Introduction")

			# The "General" category itself is left alone - helpdesk refuses to
			# delete it, and an empty category costs nothing next to four full ones.
			_ = old_category

	# The Page RECORDS are not deleted here. A Page is app code, and frappe only
	# permits deleting one in developer mode - correctly, because the record is a
	# shadow of a folder in the app. The folders are gone from the app, so
	# `bench migrate` removes the orphaned records on its own. What this does is
	# take away every way anyone still reaches them.

	# a shortcut left pointing at a deleted page is a dead link on somebody's
	# home screen, which is worse than no link at all
	for link in frappe.get_all(
		"Workspace Link",
		filters={"link_to": ["in", list(SUPERSEDED_PAGES) +
			["Dealer Conversations", "Service Command Centre"]]},
		fields=["name", "parent"],
	):
		frappe.db.delete("Workspace Link", {"name": link.name})
		done.append(f"dead link on {link.parent}")

	# helpdesk's first-run tour teaches helpdesk's concepts, not KUMAR's
	if frappe.db.exists("DocType", "HD Settings"):
		s = frappe.get_single("HD Settings")
		for flag in ("setup_complete", "initial_helpdesk_name_setup_skipped", "persona_captured"):
			if s.meta.has_field(flag):
				s.set(flag, 1)
		if s.meta.has_field("show_customer_portal_permission_notice"):
			s.set("show_customer_portal_permission_notice", 0)
		s.flags.ignore_permissions = True
		s.save(ignore_permissions=True)
		done.append("helpdesk onboarding tour dismissed")

	frappe.db.commit()
	return done


def knowledge_base():
	"""The articles a dealer reaches for, seeded from code so they ship."""
	from kumar_service.setup.knowledge import build_all as seed

	return seed()


def build_all():
	if not frappe.db.exists("DocType", "HD Settings"):
		frappe.msgprint("helpdesk is not installed on this site; skipping the desk setup")
		return
	out = {
		"brand": brand(),
		"agents": agents(),
		"ticket_types": ticket_types(),
		"ticket_fields": ticket_fields(),
		"request_type_field": request_type_field(),
		"dealer_permissions": dealer_permissions(),
		"staff_permissions": staff_permissions(),
		"dealers": dealers(),
		"retired": retire_superseded(),
		"knowledge": knowledge_base(),
	}
	frappe.db.commit()
	return out
