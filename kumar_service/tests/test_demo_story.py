"""The demo data has to tell the story a prospect will actually test.

The first filter anyone tries on the ticket list is "Raised by dealers" - and
until now every seeded claim answered "Raised by KUMAR · Administrator",
because the seed created them all as Administrator. demo_story.claims() now
hands most of them to their dealer's portal login, and the mirrored tickets
must agree with whatever it decided.
"""

import frappe
from frappe.tests import IntegrationTestCase

from kumar_service.desk_bridge import desk_installed


class TestDemoStoryClaims(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		if not frappe.db.count("Kumar Warranty Claim", {"docstatus": ["<", 2]}):
			self.skipTest("no claims on this site")

	def test_most_claims_are_raised_by_their_dealer(self):
		from kumar_service.setup import demo_story

		out = demo_story.claims()
		raised = out["raised_by"]
		self.assertEqual(out["claims"], raised["Dealer"] + raised["KUMAR"])
		# most claims come from the dealer next to the pump; a few stay with
		# staff, because a desk where no one ever rang a claim in reads staged
		self.assertGreater(raised["Dealer"], raised["KUMAR"])
		self.assertGreater(raised["KUMAR"], 0)

	def test_the_tickets_agree_with_the_claims(self):
		if not desk_installed():
			self.skipTest("helpdesk is not installed")
		from kumar_service.portal_api import _portal_users
		from kumar_service.setup import demo_story

		demo_story.claims()
		portal_users = _portal_users()
		tickets = frappe.get_all(
			"HD Ticket", filters={"custom_warranty_claim": ["is", "set"]},
			fields=["custom_warranty_claim", "custom_origin", "description"],
			limit_page_length=0,
		)
		self.assertTrue(tickets)
		for t in tickets:
			owner = frappe.db.get_value("Kumar Warranty Claim", t.custom_warranty_claim, "owner")
			expected = "Dealer" if owner in portal_users else "KUMAR"
			self.assertEqual(t.custom_origin, expected, f"{t.custom_warranty_claim}: origin")
			if expected == "Dealer":
				# the opening description must not still credit KUMAR
				self.assertNotIn("Raised by KUMAR", t.description or "",
					f"{t.custom_warranty_claim}: stale raised-by line")

	def test_it_decides_the_same_way_every_run(self):
		from kumar_service.setup import demo_story

		first = demo_story.claims()["raised_by"]
		second = demo_story.claims()["raised_by"]
		self.assertEqual(first, second)
