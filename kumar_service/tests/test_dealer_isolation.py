"""One dealer must not be able to read another dealer's business.

Every one of these assertions failed at some point, so none of them is
hypothetical:

  * Dealer            - the list was scoped by permission_query_conditions, but
                        a direct read of one document was not, because a
                        document read consults has_permission and there was no
                        has_permission hook for Dealer. Any dealer could fetch a
                        competitor's GSTIN, mobile number and credit limit by
                        name.
  * Service Visit     - carries no `dealer` field, so it had been left out of
                        the scoping altogether: every dealer could list every
                        visit in the network and read another dealer's customer,
                        technician and site findings.
  * Pump Test         - same shape. Unscoped, it exposed the works test record
    Certificate         of every pump the factory has ever built.

The tree matters as much as the isolation: a group dealer is supposed to see
its own sub-dealers, so a test that only proved "cannot read anything else"
would pass just as well if the scoping were simply broken shut.
"""

import frappe
from frappe.tests import IntegrationTestCase

from kumar_service.utils import dealer_and_descendants, user_dealer


def _a_dealer_with_a_login():
	for row in frappe.get_all("Dealer", fields=["name", "portal_user"], limit_page_length=0):
		if row.portal_user and frappe.db.exists("User", row.portal_user):
			return row
	return None


def _an_unrelated_dealer(mine):
	"""A dealer outside `mine`'s subtree - the one it must not be able to read."""
	inside = set(dealer_and_descendants(mine))
	for row in frappe.get_all("Dealer", pluck="name", limit_page_length=0):
		if row not in inside:
			return row
	return None


class TestDealerIsolation(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.row = _a_dealer_with_a_login()

	def setUp(self):
		if not self.row:
			self.skipTest("no dealer has a portal login on this site")
		self.me = self.row.name
		self.user = self.row.portal_user
		self.other = _an_unrelated_dealer(self.me)
		frappe.set_user(self.user)

	def tearDown(self):
		frappe.set_user("Administrator")

	# ------------------------------------------------------------------ Dealer

	def test_cannot_read_an_unrelated_dealer(self):
		if not self.other:
			self.skipTest("every dealer on this site is inside one subtree")
		self.assertFalse(
			frappe.has_permission("Dealer", doc=self.other, user=self.user),
			f"{self.user} can read the Dealer master of {self.other}",
		)

	def test_can_still_read_own_dealer_and_sub_dealers(self):
		for name in dealer_and_descendants(self.me):
			self.assertTrue(
				frappe.has_permission("Dealer", doc=name, user=self.user),
				f"{self.user} cannot read {name}, which is inside its own tree",
			)

	def test_dealer_list_is_the_subtree_and_nothing_more(self):
		# get_list applies permission_query_conditions; get_all deliberately does
		# NOT - it is the "I know what I am doing" call. A test that reaches for
		# get_all here would pass against a completely unscoped doctype.
		visible = set(frappe.get_list("Dealer", pluck="name", limit_page_length=0))
		self.assertEqual(visible, set(dealer_and_descendants(self.me)))

	# ----------------------------------------------------------- Service Visit

	def test_service_visits_are_scoped_to_own_tickets(self):
		mine = set(dealer_and_descendants(self.me))
		visible = frappe.get_list(
			"Service Visit", fields=["name", "service_request"], limit_page_length=0
		)
		for v in visible:
			owner = frappe.db.get_value("Service Request", v.service_request, "dealer")
			self.assertIn(
				owner, mine,
				f"{v.name} belongs to {owner}, which is outside {self.me}'s tree",
			)

	def test_cannot_read_a_foreign_service_visit(self):
		frappe.set_user("Administrator")
		foreign = None
		for v in frappe.get_all(
			"Service Visit", fields=["name", "service_request"], limit_page_length=0
		):
			owner = frappe.db.get_value("Service Request", v.service_request, "dealer")
			if owner and owner not in dealer_and_descendants(self.me):
				foreign = v.name
				break
		frappe.set_user(self.user)
		if not foreign:
			self.skipTest("no service visit belongs to another dealer on this site")
		self.assertFalse(
			frappe.has_permission("Service Visit", doc=foreign, user=self.user),
			f"{self.user} can read {foreign}, another dealer's visit",
		)

	# --------------------------------------------------- Pump Test Certificate

	def test_test_certificates_are_scoped_to_own_pumps(self):
		mine = set(dealer_and_descendants(self.me))
		for c in frappe.get_list(
			"Pump Test Certificate", fields=["name", "serial_no"], limit_page_length=0
		):
			owner = frappe.db.get_value("Serial No", c.serial_no, "custom_dealer")
			self.assertIn(
				owner, mine,
				f"{c.name} is for a pump sold by {owner}, outside {self.me}'s tree",
			)

	def test_certificate_scoping_actually_excludes_something(self):
		"""Guards against the scoping being broken shut rather than correct."""
		frappe.set_user("Administrator")
		total = frappe.db.count("Pump Test Certificate")
		frappe.set_user(self.user)
		visible = len(frappe.get_list("Pump Test Certificate", limit_page_length=0))
		if total == 0:
			self.skipTest("no test certificates on this site")
		self.assertLess(visible, total, "a dealer can see every test certificate")

	# ------------------------------------------------------------- Serial No

	def test_a_dealer_can_read_a_serial_it_sold(self):
		"""The Dealer role held no Serial No permission at all, so every desk
		page that reached a serial through the ORM died on doctype access."""
		mine = dealer_and_descendants(self.me)
		sn = frappe.get_all(
			"Serial No", filters={"custom_dealer": ["in", mine]}, pluck="name", limit=1
		)
		if not sn:
			self.skipTest("this dealer's tree has sold no serials")
		self.assertTrue(
			frappe.has_permission("Serial No", doc=sn[0], user=self.user),
			f"{self.user} cannot read {sn[0]}, a serial its own tree sold",
		)

	def test_a_dealer_cannot_read_a_serial_someone_else_sold(self):
		frappe.set_user("Administrator")
		mine = set(dealer_and_descendants(self.me))
		foreign = None
		for r in frappe.get_all(
			"Serial No", fields=["name", "custom_dealer"], limit_page_length=0
		):
			if r.custom_dealer and r.custom_dealer not in mine:
				foreign = r.name
				break
		frappe.set_user(self.user)
		if not foreign:
			self.skipTest("every sold serial belongs to this dealer's tree")
		self.assertFalse(
			frappe.has_permission("Serial No", doc=foreign, user=self.user),
			f"{self.user} can read {foreign}, another dealer's serial",
		)

	def test_a_dealer_can_never_write_a_serial(self):
		"""A pump is created in the plant. A dealer records the sale through
		Pump Registration, which has its own rules - never by editing a serial."""
		mine = dealer_and_descendants(self.me)
		sn = frappe.get_all(
			"Serial No", filters={"custom_dealer": ["in", mine]}, pluck="name", limit=1
		)
		if not sn:
			self.skipTest("this dealer's tree has sold no serials")
		self.assertFalse(
			frappe.has_permission("Serial No", ptype="write", doc=sn[0], user=self.user),
			"a dealer can write a Serial No",
		)

	# ----------------------------------------------------------- the portal API

	def test_portal_refuses_a_pump_this_dealer_did_not_sell(self):
		from kumar_service.portal_api import pump_snapshot

		frappe.set_user("Administrator")
		mine = set(dealer_and_descendants(self.me))
		foreign = None
		# it has to be a REGISTERED pump: an unregistered one is refused for a
		# different reason, and would prove nothing about isolation
		for sn in frappe.get_all(
			"Serial No",
			filters={"custom_registration": ["is", "set"]},
			fields=["name", "custom_dealer"],
			limit_page_length=0,
		):
			if sn.custom_dealer and sn.custom_dealer not in mine:
				foreign = sn.name
				break
		frappe.set_user(self.user)
		if not foreign:
			self.skipTest("every registered serial belongs to this dealer's tree")
		with self.assertRaises(frappe.PermissionError):
			pump_snapshot(foreign)

	def test_user_dealer_resolves_the_login_to_its_outlet(self):
		self.assertEqual((user_dealer(self.user) or {}).get("name"), self.me)
