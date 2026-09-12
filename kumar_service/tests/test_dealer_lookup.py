"""Pump Lookup from the dealer's counter, and the claim it can raise.

Two things this proves, both of which were wrong at some point:

  * dealer_pump_lookup gives the warranty verdict for ANY serial - that is the
    point of it, a dealer over a pump wants to know if it is covered - but hands
    back the customer's name, number and history ONLY for the dealer's own
    sales. Another shop's pump comes back as warranty-only. A lookup that leaked
    the customer would be the same class of bug as the three in
    test_dealer_isolation.

  * a claim a dealer lodges lands in Pending Review, not Draft. It used to stay
    in Draft, so the dealer was told "KUMAR will review it" while the claim sat
    invisible to every staff screen.
"""

import frappe
from frappe.tests import IntegrationTestCase

from kumar_service.utils import dealer_and_descendants


def _dealer_with_login_and_a_sale():
	for row in frappe.get_all("Dealer", fields=["name", "portal_user"], limit_page_length=0):
		if not (row.portal_user and frappe.db.exists("User", row.portal_user)):
			continue
		mine = set(dealer_and_descendants(row.name))
		sale = frappe.get_all(
			"Pump Registration",
			filters={"docstatus": 1, "dealer": ["in", list(mine)]},
			fields=["serial_no"], limit=1,
		)
		if sale:
			return row, sale[0].serial_no
	return None, None


def _a_sale_outside(mine_names):
	rows = frappe.get_all(
		"Pump Registration", filters={"docstatus": 1},
		fields=["serial_no", "dealer"], limit_page_length=0,
	)
	for r in rows:
		if r.dealer not in mine_names:
			return r.serial_no
	return None


class TestDealerLookup(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.row, cls.my_serial = _dealer_with_login_and_a_sale()

	def setUp(self):
		if not self.row:
			self.skipTest("no dealer with a login and a registered sale on this site")
		self.user = self.row.portal_user
		self.mine = set(dealer_and_descendants(self.row.name))
		frappe.set_user(self.user)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_own_pump_shows_warranty_and_the_customer(self):
		from kumar_service.portal_api import dealer_pump_lookup

		out = dealer_pump_lookup(self.my_serial)
		self.assertTrue(out["found"])
		self.assertTrue(out["mine"])
		self.assertIn(out["warranty_status"],
			("In Warranty", "Expiring Soon", "Expired", "Not Registered"))
		# the counter can see its own customer
		self.assertIn("end_customer_name", out)

	def test_another_dealers_pump_is_warranty_only(self):
		from kumar_service.portal_api import dealer_pump_lookup

		other = _a_sale_outside(self.mine)
		if not other:
			self.skipTest("every registered pump on this site is inside one tree")
		out = dealer_pump_lookup(other)
		self.assertTrue(out["found"])
		self.assertFalse(out["mine"])
		# the verdict is there...
		self.assertIn("warranty_status", out)
		# ...but nothing that identifies someone else's customer
		self.assertNotIn("end_customer_name", out)
		self.assertNotIn("end_customer_mobile", out)
		self.assertNotIn("where", out)

	def test_my_visits_stay_inside_my_tree(self):
		from kumar_service.portal_api import my_visits

		for v in my_visits():
			owner = frappe.db.get_value("Service Request", v["service_request"], "dealer")
			self.assertIn(
				owner, self.mine,
				f"{v['name']} belongs to {owner}, outside this dealer's tree",
			)

	def test_unknown_serial_is_a_clean_miss(self):
		from kumar_service.portal_api import dealer_pump_lookup

		out = dealer_pump_lookup("KP-DEFINITELY-NOT-REAL-00000")
		self.assertFalse(out["found"])

	def test_a_lodged_claim_reaches_pending_review(self):
		from kumar_service.portal_api import dealer_pump_lookup, raise_claim

		# a pump this dealer sold that is still in warranty, so a claim is real
		look = dealer_pump_lookup(self.my_serial)
		if not look.get("in_warranty"):
			self.skipTest("this dealer's sample pump is out of warranty")
		claim = raise_claim(
			serial_no=self.my_serial,
			claim_type="Part Replacement",
			technician_report="[test] bearing worn inside warranty",
		)
		name = claim["name"]
		try:
			self.assertEqual(claim["state"], "Pending Review")
			doc = frappe.get_doc("Kumar Warranty Claim", name)
			self.assertEqual(doc.workflow_state, "Pending Review")
			self.assertEqual(doc.docstatus, 1)
			# and it is now on the staff claims desk
			frappe.set_user("Administrator")
			from kumar_service.staff_api import CLAIM_OPEN
			self.assertIn(doc.workflow_state, CLAIM_OPEN)
		finally:
			frappe.set_user("Administrator")
			if frappe.db.exists("Kumar Warranty Claim", name):
				if frappe.db.get_value("Kumar Warranty Claim", name, "docstatus") == 1:
					frappe.db.set_value("Kumar Warranty Claim", name, "docstatus", 2,
						update_modified=False)
				for tk in frappe.get_all("HD Ticket",
						filters={"custom_warranty_claim": name}, pluck="name"):
					frappe.delete_doc("HD Ticket", tk, force=True, ignore_permissions=True)
				frappe.delete_doc("Kumar Warranty Claim", name, force=True,
					ignore_permissions=True, ignore_on_trash=True)
