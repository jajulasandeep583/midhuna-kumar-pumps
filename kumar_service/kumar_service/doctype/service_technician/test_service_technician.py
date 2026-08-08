import frappe
from frappe.tests import IntegrationTestCase

from kumar_service.tests import fixtures

IGNORE_TEST_RECORD_DEPENDENCIES = fixtures.LINK_DEPENDENCIES


class TestServiceTechnician(IntegrationTestCase):
	def test_create(self):
		name = fixtures.technician()
		doc = frappe.get_doc("Service Technician", name)
		self.assertEqual(doc.dealer, fixtures.DEALER_INDEPENDENT)
		self.assertTrue(doc.is_active)

	def test_validate_failure_without_a_name(self):
		doc = frappe.get_doc({"doctype": "Service Technician", "mobile_no": "9876500001"})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_duplicate_is_refused(self):
		fixtures.technician()
		doc = frappe.get_doc(
			{"doctype": "Service Technician", "technician_name": fixtures.TECHNICIAN}
		)
		self.assertRaises(frappe.DuplicateEntryError, doc.insert)

	def test_the_technicians_dealer_becomes_the_service_centre(self):
		"""A request routed to a technician inherits that technician's outlet."""
		technician = fixtures.technician()
		request = fixtures.service_request(assigned_technician=technician)
		self.assertEqual(request.service_centre, fixtures.DEALER_INDEPENDENT)
		self.assertEqual(request.status, "Assigned")

	def test_is_a_master_not_a_transaction(self):
		meta = frappe.get_meta("Service Technician")
		self.assertFalse(meta.is_submittable)
		self.assertFalse(any(p.submit or p.cancel or p.amend for p in meta.permissions))

	def test_permission_denied_for_a_user_without_roles(self):
		outsider = fixtures.outsider()
		self.assertFalse(frappe.has_permission("Service Technician", "read", user=outsider))
		self.assertFalse(frappe.has_permission("Service Technician", "create", user=outsider))

	def test_a_dealer_may_read_but_not_create_technicians(self):
		_dealer, email = fixtures.dealer_login()
		self.assertTrue(frappe.has_permission("Service Technician", "read", user=email))
		self.assertFalse(frappe.has_permission("Service Technician", "create", user=email))
