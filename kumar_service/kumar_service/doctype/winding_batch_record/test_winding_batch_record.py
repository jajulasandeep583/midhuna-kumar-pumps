import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import cint, nowdate

from kumar_service.kumar_service.doctype.winding_batch_record.winding_batch_record import STATOR_ITEM
from kumar_service.tests import fixtures

IGNORE_TEST_RECORD_DEPENDENCIES = fixtures.LINK_DEPENDENCIES


def _batch(**overrides):
	values = {
		"doctype": "Winding Batch Record",
		"batch_no": f"_KT-WD-{frappe.generate_hash(length=6).upper()}",
		"winding_date": nowdate(),
		"pump_model": fixtures.pump_model(),
		"wire_gauge_swg": "22",
		"turns_per_coil": 68,
		"oven_temp_c": 140,
		"cure_duration_min": 180,
		"ir_test_mohm": 250,
		"qty_produced": 40,
	}
	values.update(overrides)
	doc = frappe.get_doc(values)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc


class TestWindingBatchRecord(IntegrationTestCase):
	def test_create_assumes_everything_passed_until_told_otherwise(self):
		batch = _batch()
		self.assertEqual(batch.qty_passed, 40)
		self.assertEqual(cint(batch.qty_rejected), 0)

	def test_a_split_between_passed_and_rejected_is_kept_as_entered(self):
		batch = _batch(qty_passed=36, qty_rejected=4, rejection_reason="Shorted turns")
		self.assertEqual(batch.qty_passed, 36)
		self.assertEqual(batch.qty_rejected, 4)

	def test_validate_failure_when_the_counts_exceed_what_was_produced(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			_batch(qty_produced=40, qty_passed=38, qty_rejected=5, rejection_reason="x")
		self.assertIn("cannot exceed", str(caught.exception))

	def test_validate_failure_when_rejections_have_no_reason(self):
		"""A rejected stator without a reason teaches the shop floor nothing."""
		with self.assertRaises(frappe.ValidationError) as caught:
			_batch(qty_passed=36, qty_rejected=4)
		self.assertIn("rejected", str(caught.exception))

	def test_validate_failure_without_a_batch_number(self):
		doc = frappe.get_doc(
			{"doctype": "Winding Batch Record", "winding_date": nowdate(), "qty_produced": 5}
		)
		self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_the_batch_number_becomes_a_real_batch(self):
		fixtures.pump_item(STATOR_ITEM, serialised=False)
		frappe.db.set_value("Item", STATOR_ITEM, {"has_batch_no": 1, "create_new_batch": 1})

		record = _batch()
		self.assertTrue(frappe.db.exists("Batch", record.batch_no))
		self.assertEqual(
			frappe.db.get_value("Batch", record.batch_no, "custom_batch_type"), "Winding"
		)

	def test_is_a_record_not_a_transaction(self):
		meta = frappe.get_meta("Winding Batch Record")
		self.assertFalse(meta.is_submittable)
		self.assertFalse(any(p.submit or p.cancel or p.amend for p in meta.permissions))

	def test_permission_denied_for_a_user_without_roles(self):
		outsider = fixtures.outsider()
		self.assertFalse(frappe.has_permission("Winding Batch Record", "read", user=outsider))
		self.assertFalse(frappe.has_permission("Winding Batch Record", "create", user=outsider))

	def test_a_dealer_never_sees_the_winding_shop(self):
		_dealer, email = fixtures.dealer_login()
		self.assertFalse(frappe.has_permission("Winding Batch Record", "read", user=email))
