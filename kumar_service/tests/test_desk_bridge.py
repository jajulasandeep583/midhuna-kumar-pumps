"""The mirror between a Service Request and its HD Ticket.

Service Request stays the record. The desk gets a shadow of it so agents can
work a queue, and the two rules that matter are that the shadow never lies about
the pump, and that it never destroys information the request already holds.

The second is the subtle one. The desk models four states; a Service Request has
seven. An agent who opens a ticket must not thereby flatten "Awaiting Parts"
into "Open", because the desk has no way to say "Awaiting Parts" and would be
overwriting something true with something vaguer every time.
"""

import frappe
from frappe.tests import IntegrationTestCase

from kumar_service.desk_bridge import desk_installed


def _a_request():
	rows = frappe.get_all(
		"Service Request", filters={"docstatus": ["<", 2]},
		fields=["name", "status", "serial_no", "dealer"], limit=1,
	)
	return rows[0] if rows else None


class TestDeskBridge(IntegrationTestCase):
	def setUp(self):
		if not desk_installed():
			self.skipTest("helpdesk is not installed on this site")
		self.sr = _a_request()
		if not self.sr:
			self.skipTest("no service request on this site")
		self.ticket = frappe.db.get_value(
			"HD Ticket", {"custom_service_request": self.sr.name}, "name"
		)
		if not self.ticket:
			self.skipTest("this request has not been mirrored")
		self.sr_status = frappe.db.get_value("Service Request", self.sr.name, "status")
		self.tk_status = frappe.db.get_value("HD Ticket", self.ticket, "status")

	def tearDown(self):
		if getattr(self, "sr", None):
			frappe.db.set_value("Service Request", self.sr.name, "status", self.sr_status)
		if getattr(self, "ticket", None):
			frappe.db.set_value("HD Ticket", self.ticket, "status", self.tk_status)

	# ------------------------------------------------------------- the mirror

	def test_every_open_request_has_a_ticket(self):
		missing = []
		for name in frappe.get_all(
			"Service Request", filters={"docstatus": ["<", 2]}, pluck="name"
		):
			if not frappe.db.exists("HD Ticket", {"custom_service_request": name}):
				missing.append(name)
		self.assertEqual(missing, [], f"{len(missing)} requests have no ticket")

	def test_the_ticket_carries_the_pump(self):
		t = frappe.db.get_value(
			"HD Ticket", self.ticket,
			["custom_serial_no", "custom_dealer", "custom_warranty"], as_dict=True,
		)
		self.assertEqual(t.custom_serial_no, self.sr.serial_no)
		self.assertEqual(t.custom_dealer, self.sr.dealer)
		self.assertIn(t.custom_warranty, ("In Warranty", "Out of Warranty"))

	def test_one_ticket_per_request_however_often_it_is_saved(self):
		doc = frappe.get_doc("Service Request", self.sr.name)
		doc.save(ignore_permissions=True)
		doc.save(ignore_permissions=True)
		self.assertEqual(
			frappe.db.count("HD Ticket", {"custom_service_request": self.sr.name}), 1
		)

	def test_a_sub_dealers_request_still_mirrors(self):
		"""The mirror silently stopped working for sub-dealers.

		HD Ticket refuses a customer that is not among the ticket contact's own
		customers. In a dealer tree that pair is legitimately mismatched: a
		sub-dealer with no login of its own is handled by its parent, so the
		ticket carries the sub-dealer as customer - true, they sold the pump -
		and the parent's login as contact. Every request from such an outlet
		failed to mirror, and because the bridge logs rather than raises, it
		failed quietly.
		"""
		missing = []
		for name in frappe.get_all(
			"Service Request", filters={"docstatus": ["<", 2]}, pluck="name"
		):
			if not frappe.db.exists("HD Ticket", {"custom_service_request": name}):
				missing.append(name)
		self.assertEqual(
			missing, [], f"{len(missing)} requests never reached the desk: {missing[:5]}"
		)

	def test_the_contact_is_a_member_of_the_outlet_on_every_ticket(self):
		"""The condition HD Ticket actually enforces, asserted directly."""
		from kumar_service.hd.utils import get_customers

		for t in frappe.get_all(
			"HD Ticket",
			filters={"custom_service_request": ["is", "set"]},
			fields=["name", "customer", "contact"],
			limit=40,
		):
			if not (t.customer and t.contact):
				continue
			self.assertIn(
				t.customer,
				get_customers(contact=t.contact),
				f"{t.name}: contact {t.contact} is not a member of {t.customer}",
			)

	# --------------------------------------------------------- status upward

	def test_resolving_in_the_desk_resolves_the_request(self):
		frappe.db.set_value("Service Request", self.sr.name, "status", "In Progress")
		t = frappe.get_doc("HD Ticket", self.ticket)
		t.status = "Resolved"
		t.save(ignore_permissions=True)
		self.assertEqual(
			frappe.db.get_value("Service Request", self.sr.name, "status"), "Resolved"
		)

	def test_the_desk_never_flattens_a_more_specific_open_state(self):
		"""The whole reason set_status is conservative."""
		for specific in ("Assigned", "In Progress", "Awaiting Parts"):
			frappe.db.set_value("Service Request", self.sr.name, "status", specific)
			t = frappe.get_doc("HD Ticket", self.ticket)
			t.status = "Open"
			t.save(ignore_permissions=True)
			self.assertEqual(
				frappe.db.get_value("Service Request", self.sr.name, "status"),
				specific,
				f"the desk overwrote {specific} with Open",
			)

	def test_a_cancelled_request_is_never_revived_by_the_desk(self):
		frappe.db.set_value("Service Request", self.sr.name, "status", "Cancelled")
		t = frappe.get_doc("HD Ticket", self.ticket)
		t.status = "Open"
		t.save(ignore_permissions=True)
		self.assertEqual(
			frappe.db.get_value("Service Request", self.sr.name, "status"), "Cancelled"
		)

	# ------------------------------------------------------------- resilience

	def test_the_bridge_cannot_stop_a_request_being_saved(self):
		"""A desk having a bad day must not stop a dealer raising a complaint."""
		import kumar_service.desk_bridge as bridge

		original = bridge._mirror
		bridge._mirror = lambda *a, **k: 1 / 0
		try:
			doc = frappe.get_doc("Service Request", self.sr.name)
			doc.save(ignore_permissions=True)   # must not raise
		finally:
			bridge._mirror = original
