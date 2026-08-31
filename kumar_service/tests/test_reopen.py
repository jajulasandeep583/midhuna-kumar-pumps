"""A dealer's reply reopens a ticket that was already closed.

The staff queue lists open tickets, and who KUMAR owes an answer to is derived
from who wrote last. Both work - but only for a ticket that is still open. A
dealer replying "it has failed again" to a Resolved or Closed request was
writing into a thread that had already dropped off the queue, so nobody was
going to read it.

Warranty claims are deliberately excluded: their Settled and Rejected workflow
states have no outgoing transition, so reopening one means adding a Workflow
Transition, not writing the field behind the workflow's back.
"""

import frappe
from frappe.tests import IntegrationTestCase


def _a_dealer_with_a_request():
	for row in frappe.get_all("Dealer", fields=["name", "portal_user"], limit_page_length=0):
		if not row.portal_user or not frappe.db.exists("User", row.portal_user):
			continue
		sr = frappe.get_all(
			"Service Request",
			filters={"dealer": row.name, "docstatus": ["<", 2]},
			fields=["name", "status"],
			limit=1,
		)
		if sr:
			return row, sr[0]
	return None, None


class TestReopenOnReply(IntegrationTestCase):
	def setUp(self):
		self.dealer, self.sr = _a_dealer_with_a_request()
		if not self.sr:
			self.skipTest("no dealer on this site owns a service request")
		self.original = frappe.db.get_value("Service Request", self.sr.name, "status")

	def tearDown(self):
		if self.sr:
			frappe.db.set_value("Service Request", self.sr.name, "status", self.original)
		frappe.set_user("Administrator")

	def _reply(self, text):
		from kumar_service.portal_api import post_reply

		frappe.set_user(self.dealer.portal_user)
		try:
			return post_reply("complaint", self.sr.name, text)
		finally:
			frappe.set_user("Administrator")

	def test_replying_to_a_resolved_request_reopens_it(self):
		frappe.db.set_value("Service Request", self.sr.name, "status", "Resolved")
		out = self._reply("The pump has failed again, same noise.")
		self.assertTrue(out["reopened"])
		self.assertEqual(
			frappe.db.get_value("Service Request", self.sr.name, "status"), "Open"
		)

	def test_replying_to_a_closed_request_reopens_it(self):
		frappe.db.set_value("Service Request", self.sr.name, "status", "Closed")
		out = self._reply("Still not fixed.")
		self.assertTrue(out["reopened"])
		self.assertEqual(
			frappe.db.get_value("Service Request", self.sr.name, "status"), "Open"
		)

	def test_reopening_leaves_a_trail(self):
		frappe.db.set_value("Service Request", self.sr.name, "status", "Closed")
		self._reply("It is leaking again.")
		notes = frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "Service Request",
				"reference_name": self.sr.name,
				"comment_type": "Info",
			},
			pluck="content",
		)
		self.assertTrue(
			any("Reopened" in (n or "") for n in notes),
			"reopening a ticket left no note explaining why the status moved",
		)

	def test_an_open_request_is_left_alone(self):
		"""Who is waiting is derived from who wrote last, so an open ticket needs
		no status change - and rewriting it would lose 'Awaiting Parts'."""
		frappe.db.set_value("Service Request", self.sr.name, "status", "Awaiting Parts")
		out = self._reply("Any update on the part?")
		self.assertFalse(out["reopened"])
		self.assertEqual(
			frappe.db.get_value("Service Request", self.sr.name, "status"),
			"Awaiting Parts",
		)

	def test_the_reply_itself_still_lands_on_the_thread(self):
		frappe.db.set_value("Service Request", self.sr.name, "status", "Resolved")
		out = self._reply("Reopening this one please.")
		self.assertTrue(
			any("Reopening this one" in (m.get("message") or "") for m in out["thread"]),
			"the dealer's message did not appear in the thread it reopened",
		)
