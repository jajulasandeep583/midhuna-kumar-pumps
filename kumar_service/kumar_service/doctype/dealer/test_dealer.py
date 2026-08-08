import frappe
from frappe.tests import IntegrationTestCase

from kumar_service.tests import fixtures
from kumar_service.utils import CH_DEALER, CH_DIRECT, dealer_and_descendants, sale_channel_for, user_dealer

IGNORE_TEST_RECORD_DEPENDENCIES = fixtures.LINK_DEPENDENCIES


class TestDealer(IntegrationTestCase):
	def test_create(self):
		name = fixtures.dealer()
		doc = frappe.get_doc("Dealer", name)
		self.assertEqual(doc.status, "Active")
		self.assertFalse(doc.is_own_outlet)
		# nested set stamps its bounds on insert
		self.assertIsNotNone(doc.lft)
		self.assertGreater(doc.rgt, doc.lft)

	def test_validate_failure_without_a_name(self):
		doc = frappe.get_doc({"doctype": "Dealer", "dealer_type": "Dealer"})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_a_portal_user_cannot_serve_two_dealers(self):
		"""One login, one outlet - otherwise row-level isolation is undecidable."""
		email = fixtures.user("_kt.shared@kumartest.local", roles=["Dealer"])
		fixtures.dealer("_KT Dealer First", portal_user=email)

		clash = frappe.get_doc(
			{"doctype": "Dealer", "dealer_name": "_KT Dealer Second", "portal_user": email}
		)
		self.assertRaises(frappe.ValidationError, clash.insert)

	def test_subtree_covers_children(self):
		parent = frappe.get_doc(
			{"doctype": "Dealer", "dealer_name": "_KT Dealer Parent", "is_group": 1}
		).insert(ignore_permissions=True)
		child = frappe.get_doc(
			{
				"doctype": "Dealer",
				"dealer_name": "_KT Dealer Child",
				"parent_dealer": parent.name,
			}
		).insert(ignore_permissions=True)

		subtree = dealer_and_descendants(parent.name)
		self.assertIn(parent.name, subtree)
		self.assertIn(child.name, subtree)
		self.assertNotIn(fixtures.dealer(), subtree)

	def test_ownership_decides_the_sale_channel(self):
		independent = fixtures.dealer(fixtures.DEALER_INDEPENDENT, is_own_outlet=0)
		branch = fixtures.dealer(fixtures.DEALER_OWN, is_own_outlet=1)

		self.assertEqual(sale_channel_for(independent), CH_DEALER)
		self.assertEqual(sale_channel_for(branch), CH_DIRECT)

	def test_portal_user_resolves_back_to_its_dealer(self):
		name, email = fixtures.dealer_login()
		self.assertEqual(user_dealer(email).name, name)
		self.assertIsNone(user_dealer(fixtures.outsider()))

	def test_is_a_master_not_a_transaction(self):
		meta = frappe.get_meta("Dealer")
		self.assertFalse(meta.is_submittable)
		self.assertFalse(any(p.submit or p.cancel or p.amend for p in meta.permissions))

	def test_permission_denied_for_a_user_without_roles(self):
		outsider = fixtures.outsider()
		self.assertFalse(frappe.has_permission("Dealer", "read", user=outsider))
		self.assertFalse(frappe.has_permission("Dealer", "create", user=outsider))

	def test_a_dealer_sees_only_its_own_subtree_in_the_list(self):
		mine, email = fixtures.dealer_login()
		theirs, _ = fixtures.rival_login()

		# get_list, not get_all - get_all deliberately ignores permissions
		with self.set_user(email):
			visible = frappe.get_list("Dealer", pluck="name", limit_page_length=0)

		self.assertIn(mine, visible)
		self.assertNotIn(theirs, visible)
