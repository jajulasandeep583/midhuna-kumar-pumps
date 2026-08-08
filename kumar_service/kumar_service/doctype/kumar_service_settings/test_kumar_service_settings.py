import frappe
from frappe.tests import IntegrationTestCase

from kumar_service.tests import fixtures
from kumar_service.utils import setting, validate_serial_format, warranty_months_for

IGNORE_TEST_RECORD_DEPENDENCIES = fixtures.LINK_DEPENDENCIES


class TestKumarServiceSettings(IntegrationTestCase):
	def test_the_single_exists_and_carries_the_shipped_defaults(self):
		doc = frappe.get_single("Kumar Service Settings")
		self.assertEqual(doc.doctype, "Kumar Service Settings")
		self.assertTrue(doc.default_warranty_months)
		self.assertIn(doc.warranty_from, ("Sale Date", "Manufacturing Date"))

	def test_setting_reads_through_with_a_fallback(self):
		"""A blank setting must fall back rather than return an empty string -
		half the engine multiplies these numbers."""
		self.assertEqual(
			setting("default_warranty_months"),
			frappe.db.get_single_value("Kumar Service Settings", "default_warranty_months"),
		)
		with self.change_settings("Kumar Service Settings", default_service_centre=""):
			self.assertEqual(setting("default_service_centre", "_KT fallback"), "_KT fallback")

	def test_settings_are_the_last_resort_for_warranty_months(self):
		"""Item beats model, model beats category, category beats settings -
		this proves the bottom of that chain, and that nothing is hardcoded."""
		bare_category = frappe.get_doc(
			{
				"doctype": "Pump Category",
				"category_name": "_KT Category Without Warranty",
				"default_warranty_months": 0,
			}
		).insert(ignore_permissions=True)
		bare_model = frappe.get_doc(
			{
				"doctype": "Pump Model",
				"model_code": "_KT-MODEL-NO-WARRANTY",
				"pump_category": bare_category.name,
				"hp": 2,
				"warranty_months": 0,
			}
		).insert(ignore_permissions=True)

		with self.change_settings("Kumar Service Settings", default_warranty_months=30):
			self.assertEqual(warranty_months_for(bare_model.name), 30)

	def test_the_serial_format_lives_in_settings_not_in_code(self):
		with self.change_settings(
			"Kumar Service Settings", serial_format_template=r"^_KT-OK-\d{3}$"
		):
			self.assertTrue(validate_serial_format("_KT-OK-123"))
			self.assertFalse(validate_serial_format("KP-ANYTHING-ELSE"))

	def test_a_single_cannot_be_submitted(self):
		meta = frappe.get_meta("Kumar Service Settings")
		self.assertTrue(meta.issingle)
		self.assertFalse(meta.is_submittable)

	def test_permission_denied_for_a_user_without_roles(self):
		outsider = fixtures.outsider()
		self.assertFalse(frappe.has_permission("Kumar Service Settings", "read", user=outsider))
		self.assertFalse(frappe.has_permission("Kumar Service Settings", "write", user=outsider))

	def test_a_dealer_cannot_touch_the_settings(self):
		"""Warranty months and SLA hours are set here - a dealer editing them
		would be editing its own obligations."""
		_dealer, email = fixtures.dealer_login()
		self.assertFalse(frappe.has_permission("Kumar Service Settings", "write", user=email))
