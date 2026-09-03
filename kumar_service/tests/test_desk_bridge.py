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


class TestOneThread(IntegrationTestCase):
	"""The request's thread and the ticket's thread are the same thread.

	A dealer writes through the portal, a visit gets booked, a claim gets
	decided: all of that used to live as Comments on the request, invisible on
	the ticket page. And an agent typing on the ticket page used to leave no
	trace on the request. Now each side mirrors onto the other, exactly once.
	"""

	def setUp(self):
		if not desk_installed():
			self.skipTest("helpdesk is not installed on this site")
		self.sr = _a_request()
		if not self.sr:
			self.skipTest("no service request on this site")
		self.ticket = frappe.db.get_value("HD Ticket", {"custom_service_request": self.sr.name}, "name")
		if not self.ticket:
			self.skipTest("this request has not been mirrored")
		self.saved = frappe.db.get_value(
			"Service Request", self.sr.name, ["status", "first_response_on", "resolved_on"], as_dict=True
		)
		self.tk_status = frappe.db.get_value("HD Ticket", self.ticket, "status")
		self.made = []  # (doctype, name) to delete
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		for doctype, name in reversed(self.made):
			frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
		frappe.db.set_value("Service Request", self.sr.name, dict(self.saved), update_modified=False)
		frappe.db.set_value("HD Ticket", self.ticket, "status", self.tk_status, update_modified=False)

	def _ticket_comms(self):
		return frappe.get_all(
			"Communication",
			filters={"reference_doctype": "HD Ticket", "reference_name": self.ticket},
			fields=["name", "content", "message_id", "sent_or_received", "communication_medium"],
			order_by="creation desc",
		)

	def _sr_comments(self):
		return frappe.get_all(
			"Comment",
			filters={"reference_doctype": "Service Request", "reference_name": self.sr.name,
				"comment_type": "Comment"},
			fields=["name", "content"], order_by="creation desc",
		)

	# ---------------------------------------------------- request -> ticket

	def test_a_message_on_the_request_appears_on_the_ticket(self):
		from kumar_service.portal_api import add_reply

		text = f"one-thread test {frappe.generate_hash(length=6)}"
		before = len(self._ticket_comms())
		comment = add_reply("Service Request", self.sr.name, text)
		self.made.append(("Comment", comment))
		comms = self._ticket_comms()
		self.assertEqual(len(comms), before + 1, "the message did not reach the ticket")
		top = comms[0]
		self.made.append(("Communication", top.name))
		self.assertIn(text, top.content)
		self.assertEqual(top.message_id, f"kumar-comment:{comment}", "not marked as a mirror")
		# a re-run of the backfill must not mirror it a second time
		from kumar_service.desk_bridge import backfill_thread
		backfill_thread()
		self.assertEqual(len(self._ticket_comms()), before + 1, "mirrored twice")

	# ---------------------------------------------------- ticket -> request

	def _agent_writes_on_ticket(self, sent_or_received, sender, text):
		doc = frappe.get_doc({
			"doctype": "Communication", "communication_type": "Communication",
			"communication_medium": "Email", "sent_or_received": sent_or_received,
			"subject": "Re: ticket", "content": f"<p>{text}</p>", "sender": sender,
			"reference_doctype": "HD Ticket", "reference_name": self.ticket,
		}).insert(ignore_permissions=True)
		self.made.append(("Communication", doc.name))
		return doc

	def test_an_agent_reply_on_the_ticket_lands_on_the_request_and_stamps_the_sla(self):
		frappe.db.set_value("Service Request", self.sr.name, "first_response_on", None, update_modified=False)
		before = len(self._sr_comments())
		text = f"agent from the ticket page {frappe.generate_hash(length=6)}"
		frappe.set_user("service.manager@kumarpumps.local")
		doc = self._agent_writes_on_ticket("Sent", "service.manager@kumarpumps.local", text)
		frappe.set_user("Administrator")

		comments = self._sr_comments()
		self.assertEqual(len(comments), before + 1, "the agent's words never reached the request")
		self.made.append(("Comment", comments[0].name))
		self.assertIn(text, comments[0].content)
		self.assertTrue(
			frappe.db.get_value("Service Request", self.sr.name, "first_response_on"),
			"an agent's first reply on the ticket must stamp the SLA",
		)
		# the original row is marked, and nothing bounced back as a second row
		self.assertTrue(frappe.db.get_value("Communication", doc.name, "message_id").startswith("kumar-comment:"))
		echoes = [c for c in self._ticket_comms() if c.communication_medium == "Chat" and text in (c.content or "")]
		self.assertEqual(echoes, [], "the agent's reply was echoed back onto the ticket")

	def test_a_dealer_reply_on_the_ticket_reopens_a_settled_request(self):
		from kumar_service.tests.test_reopen import _a_dealer_with_a_request

		dealer, sr = _a_dealer_with_a_request()
		if not dealer:
			self.skipTest("no dealer with a portal user and a request")
		ticket = frappe.db.get_value("HD Ticket", {"custom_service_request": sr.name}, "name")
		if not ticket:
			self.skipTest("the dealer's request has not been mirrored")
		saved = frappe.db.get_value("Service Request", sr.name, ["status", "resolved_on"], as_dict=True)
		tk_saved = frappe.db.get_value("HD Ticket", ticket, "status")
		try:
			frappe.db.set_value("Service Request", sr.name, "status", "Resolved", update_modified=False)
			frappe.db.set_value("HD Ticket", ticket, "status", "Resolved", update_modified=False)
			frappe.set_user(dealer.portal_user)
			doc = frappe.get_doc({
				"doctype": "Communication", "communication_type": "Communication",
				"communication_medium": "Email", "sent_or_received": "Received",
				"subject": "Re", "content": "<p>Still leaking after the visit.</p>",
				"sender": dealer.portal_user, "reference_doctype": "HD Ticket", "reference_name": ticket,
			}).insert(ignore_permissions=True)
			frappe.set_user("Administrator")
			self.made.append(("Communication", doc.name))
			c = frappe.db.get_value("Communication", doc.name, "message_id") or ""
			if c.startswith("kumar-comment:"):
				self.made.append(("Comment", c.split(":", 1)[1]))
			self.assertEqual(frappe.db.get_value("Service Request", sr.name, "status"), "Open",
				"a dealer writing on a settled ticket must reopen the request")
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Service Request", sr.name, dict(saved), update_modified=False)
			frappe.db.set_value("HD Ticket", ticket, "status", tk_saved, update_modified=False)

	# ---------------------------------------------------- claims

	def test_every_claim_has_a_ticket_of_its_own(self):
		missing, wrong_type = [], []
		for name in frappe.get_all("Kumar Warranty Claim", filters={"docstatus": ["<", 2]}, pluck="name"):
			t = frappe.db.get_value("HD Ticket", {"custom_warranty_claim": name}, ["name", "ticket_type"], as_dict=True)
			if not t:
				missing.append(name)
			elif t.ticket_type != "Warranty Claim":
				wrong_type.append(name)
		self.assertEqual(missing, [], f"{len(missing)} claims have no ticket")
		self.assertEqual(wrong_type, [], "claim tickets must be typed Warranty Claim")

	def test_a_claims_thread_is_on_its_ticket(self):
		"""Every Comment on a claim - the dealer's, the decision, the visit - is on its ticket."""
		short = []
		for name in frappe.get_all("Kumar Warranty Claim", filters={"docstatus": ["<", 2]}, pluck="name"):
			ticket = frappe.db.get_value("HD Ticket", {"custom_warranty_claim": name}, "name")
			if not ticket:
				continue
			n_comments = frappe.db.count("Comment", {"reference_doctype": "Kumar Warranty Claim",
				"reference_name": name, "comment_type": "Comment"})
			n_mirrored = frappe.db.count("Communication", {"reference_doctype": "HD Ticket",
				"reference_name": ticket, "message_id": ["like", "kumar-comment:%"]})
			if n_mirrored < n_comments:
				short.append((name, n_comments, n_mirrored))
		self.assertEqual(short, [], "claim comments missing from their ticket")
