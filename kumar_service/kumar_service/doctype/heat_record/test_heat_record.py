import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from kumar_service.kumar_service.doctype.heat_record.heat_record import CASING_ITEM
from kumar_service.tests import fixtures

IGNORE_TEST_RECORD_DEPENDENCIES = fixtures.LINK_DEPENDENCIES

IN_SPEC = [
	{"element": "C", "value_pct": 3.40, "spec_min": 3.20, "spec_max": 3.60},
	{"element": "Si", "value_pct": 1.80, "spec_min": 1.60, "spec_max": 2.20},
	{"element": "P", "value_pct": 0.06, "spec_min": 0.0, "spec_max": 0.12},
	{"element": "S", "value_pct": 0.08, "spec_min": 0.0, "spec_max": 0.12},
]

OUT_OF_SPEC = IN_SPEC[:3] + [
	{"element": "S", "value_pct": 0.19, "spec_min": 0.0, "spec_max": 0.12},
]


def _heat(readings=None, submit_state="Draft", **overrides):
	values = {
		"doctype": "Heat Record",
		"heat_no": f"_KT-HT-{frappe.generate_hash(length=6).upper()}",
		"heat_date": nowdate(),
		"shift": "A",
		"target_grade": "FG 200",
		"charge_weight_kg": 900,
		"status": submit_state,
		"spectro_readings": readings if readings is not None else list(IN_SPEC),
	}
	values.update(overrides)
	doc = frappe.get_doc(values)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc


class TestHeatRecord(IntegrationTestCase):
	def test_create_marks_each_reading_against_its_spec(self):
		heat = _heat()
		self.assertTrue(all(r.within_spec for r in heat.spectro_readings))
		self.assertTrue(heat.all_within_spec)

	def test_an_element_with_no_stated_maximum_is_not_out_of_spec(self):
		"""A blank limit means 'not specified', not 'must be under zero'."""
		heat = _heat(
			readings=[
				{"element": "C", "value_pct": 3.40, "spec_min": 3.20, "spec_max": 3.60},
				{"element": "Cu", "value_pct": 0.35},
			]
		)
		self.assertTrue(all(r.within_spec for r in heat.spectro_readings))
		self.assertTrue(heat.all_within_spec)

	def test_a_reading_outside_its_band_is_flagged(self):
		heat = _heat(readings=list(OUT_OF_SPEC))
		flagged = [r.element for r in heat.spectro_readings if not r.within_spec]
		self.assertEqual(flagged, ["S"])
		self.assertFalse(heat.all_within_spec)

	def test_carbon_equivalent_is_computed(self):
		"""CE = C + (Si + P) / 3 - the number the foundry judges a melt on."""
		heat = _heat()
		self.assertEqual(heat.carbon_equivalent, round(3.40 + (1.80 + 0.06) / 3.0, 3))

	def test_validate_failure_approving_a_heat_with_no_readings(self):
		doc = frappe.get_doc(
			{
				"doctype": "Heat Record",
				"heat_no": "_KT-HT-NO-READINGS",
				"heat_date": nowdate(),
				"status": "Approved for Pouring",
			}
		)
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.insert(ignore_permissions=True)
		self.assertIn("spectrometer", str(caught.exception))

	def test_validate_failure_approving_out_of_spec_without_a_reason(self):
		"""Chemistry can be waived, but never silently."""
		with self.assertRaises(frappe.ValidationError) as caught:
			_heat(readings=list(OUT_OF_SPEC), submit_state="Approved for Pouring")
		self.assertIn("out of spec", str(caught.exception))

	def test_out_of_spec_can_be_released_with_a_recorded_override(self):
		heat = _heat(
			readings=list(OUT_OF_SPEC),
			submit_state="Approved for Pouring",
			override_reason="Sulphur marginal; foundry head accepted for non-critical casings.",
		)
		self.assertEqual(heat.status, "Approved for Pouring")
		self.assertEqual(heat.lab_approved_by, frappe.session.user)
		self.assertTrue(heat.lab_approved_on)

	def test_validate_failure_without_a_heat_number(self):
		doc = frappe.get_doc({"doctype": "Heat Record", "heat_date": nowdate()})
		self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_approving_turns_the_heat_into_a_real_batch(self):
		"""The heat number has to become a Batch, or castings cannot carry it."""
		fixtures.pump_item(CASING_ITEM, serialised=False)
		frappe.db.set_value("Item", CASING_ITEM, {"has_batch_no": 1, "create_new_batch": 1})

		heat = _heat(submit_state="Approved for Pouring")
		self.assertTrue(frappe.db.exists("Batch", heat.heat_no))
		batch = frappe.get_doc("Batch", heat.heat_no)
		self.assertEqual(batch.custom_batch_type, "Heat")
		self.assertEqual(batch.custom_heat_record, heat.name)

	def test_a_draft_heat_makes_no_batch(self):
		heat = _heat()
		self.assertFalse(frappe.db.exists("Batch", heat.heat_no))

	def test_is_a_record_not_a_transaction(self):
		meta = frappe.get_meta("Heat Record")
		self.assertFalse(meta.is_submittable)
		self.assertFalse(any(p.submit or p.cancel or p.amend for p in meta.permissions))

	def test_permission_denied_for_a_user_without_roles(self):
		outsider = fixtures.outsider()
		self.assertFalse(frappe.has_permission("Heat Record", "read", user=outsider))
		self.assertFalse(frappe.has_permission("Heat Record", "create", user=outsider))

	def test_a_dealer_never_sees_the_foundry(self):
		"""Genealogy is ours. A dealer has no business in the melt log."""
		_dealer, email = fixtures.dealer_login()
		self.assertFalse(frappe.has_permission("Heat Record", "read", user=email))
