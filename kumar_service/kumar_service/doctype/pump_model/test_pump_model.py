import frappe
from frappe.tests import IntegrationTestCase

from kumar_service.tests import fixtures
from kumar_service.utils import warranty_months_for

IGNORE_TEST_RECORD_DEPENDENCIES = fixtures.LINK_DEPENDENCIES


class TestPumpModel(IntegrationTestCase):
	def test_create(self):
		name = fixtures.pump_model()
		doc = frappe.get_doc("Pump Model", name)
		self.assertEqual(doc.pump_category, fixtures.CATEGORY)
		self.assertEqual(doc.hp, 5.0)
		self.assertEqual(doc.phase, "Three Phase")
		self.assertTrue(doc.is_active)

	def test_validate_failure_without_category(self):
		doc = frappe.get_doc(
			{"doctype": "Pump Model", "model_code": "_KT-NO-CATEGORY", "hp": 3}
		)
		self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_validate_failure_without_hp(self):
		"""HP is what every downstream screen groups and prices on."""
		doc = frappe.get_doc(
			{
				"doctype": "Pump Model",
				"model_code": "_KT-NO-HP",
				"pump_category": fixtures.pump_category(),
			}
		)
		self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_duplicate_model_code_is_refused(self):
		fixtures.pump_model()
		doc = frappe.get_doc(
			{
				"doctype": "Pump Model",
				"model_code": fixtures.MODEL,
				"pump_category": fixtures.pump_category(),
				"hp": 5,
			}
		)
		self.assertRaises(frappe.DuplicateEntryError, doc.insert)

	def test_model_warranty_beats_the_category(self):
		fixtures.pump_category()
		override = frappe.get_doc(
			{
				"doctype": "Pump Model",
				"model_code": "_KT-MODEL-LONG-WARRANTY",
				"pump_category": fixtures.CATEGORY,
				"hp": 7.5,
				"warranty_months": 36,
			}
		).insert(ignore_permissions=True)

		self.assertEqual(warranty_months_for(override.name), 36)
		self.assertEqual(warranty_months_for(fixtures.pump_model()), 18)

	def test_performance_curve_rows_persist(self):
		doc = frappe.get_doc("Pump Model", fixtures.pump_model())
		doc.append("performance_curve", {"head_m": 30, "discharge": 900, "efficiency_pct": 52})
		doc.append("performance_curve", {"head_m": 45, "discharge": 600, "efficiency_pct": 48})
		doc.save(ignore_permissions=True)

		reloaded = frappe.get_doc("Pump Model", doc.name)
		self.assertEqual(len(reloaded.performance_curve), 2)
		self.assertEqual(reloaded.performance_curve[1].head_m, 45)

	def test_is_a_master_not_a_transaction(self):
		meta = frappe.get_meta("Pump Model")
		self.assertFalse(meta.is_submittable)
		self.assertFalse(any(p.submit or p.cancel or p.amend for p in meta.permissions))

	def test_permission_denied_for_a_user_without_roles(self):
		outsider = fixtures.outsider()
		self.assertFalse(frappe.has_permission("Pump Model", "create", user=outsider))
		self.assertFalse(frappe.has_permission("Pump Model", "write", user=outsider))

	def test_a_dealer_may_read_models_but_not_edit_them(self):
		_dealer, email = fixtures.dealer_login()
		self.assertTrue(frappe.has_permission("Pump Model", "read", user=email))
		self.assertFalse(frappe.has_permission("Pump Model", "write", user=email))
