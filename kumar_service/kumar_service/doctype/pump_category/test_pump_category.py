import frappe
from frappe.tests import IntegrationTestCase

from kumar_service.tests import fixtures
from kumar_service.utils import warranty_months_for

IGNORE_TEST_RECORD_DEPENDENCIES = fixtures.LINK_DEPENDENCIES


class TestPumpCategory(IntegrationTestCase):
	def test_create(self):
		name = fixtures.pump_category()
		doc = frappe.get_doc("Pump Category", name)
		self.assertEqual(doc.name, name)
		self.assertEqual(doc.default_warranty_months, 18)
		self.assertTrue(doc.is_active)

	def test_validate_failure_without_name(self):
		"""The category names itself from the field, so a blank one cannot save."""
		doc = frappe.get_doc({"doctype": "Pump Category", "default_warranty_months": 12})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_duplicate_is_refused(self):
		fixtures.pump_category()
		doc = frappe.get_doc(
			{"doctype": "Pump Category", "category_name": fixtures.CATEGORY}
		)
		self.assertRaises(frappe.DuplicateEntryError, doc.insert)

	def test_is_a_master_not_a_transaction(self):
		"""No submit/cancel here - a category is a master, and its permission
		rows must not hand anyone a docstatus to play with."""
		meta = frappe.get_meta("Pump Category")
		self.assertFalse(meta.is_submittable)
		self.assertFalse(any(p.submit or p.cancel or p.amend for p in meta.permissions))

	def test_warranty_falls_back_to_the_category(self):
		"""The model carries no months of its own, so the category decides."""
		model = fixtures.pump_model()
		self.assertEqual(warranty_months_for(model), 18)

	def test_permission_denied_for_a_user_without_roles(self):
		outsider = fixtures.outsider()
		self.assertFalse(frappe.has_permission("Pump Category", "create", user=outsider))
		self.assertFalse(frappe.has_permission("Pump Category", "write", user=outsider))
