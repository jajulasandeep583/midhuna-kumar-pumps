"""The five child DocTypes.

A child table has no life of its own - it cannot be fetched, submitted or
permissioned on its own - so each one is exercised through the parent that owns
it. What is worth asserting is that the rows persist, that the derived columns
on them are computed rather than typed, and that none of them has quietly
acquired standalone permissions.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime, nowdate

from kumar_service.tests import fixtures

CHILD_DOCTYPES = (
	"Pump Model Spec Point",
	"Heat Spectro Reading",
	"Test Duty Point",
	"Service Part Used",
	"Claim Part Row",
)


class TestChildTables(IntegrationTestCase):
	def test_every_child_table_is_declared_as_one(self):
		for doctype in CHILD_DOCTYPES:
			meta = frappe.get_meta(doctype)
			self.assertTrue(meta.istable, f"{doctype} is not marked as a child table")
			self.assertFalse(meta.is_submittable, f"{doctype} should not be submittable")
			self.assertEqual(
				meta.permissions, [], f"{doctype} should have no permissions of its own"
			)

	def test_a_child_row_cannot_be_inserted_on_its_own(self):
		doc = frappe.get_doc({"doctype": "Test Duty Point", "head_m": 30, "discharge_lpm": 900})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_pump_model_spec_point_carries_a_performance_curve(self):
		model = frappe.get_doc("Pump Model", fixtures.pump_model())
		model.set("performance_curve", [])
		for head, discharge in ((10, 1400), (20, 1100), (30, 900), (40, 620)):
			model.append(
				"performance_curve",
				{"head_m": head, "discharge": discharge, "efficiency_pct": 50, "input_kw": 3.7},
			)
		model.save(ignore_permissions=True)

		curve = frappe.get_doc("Pump Model", model.name).performance_curve
		self.assertEqual([r.head_m for r in curve], [10, 20, 30, 40])
		self.assertEqual([r.idx for r in curve], [1, 2, 3, 4])

	def test_heat_spectro_reading_gets_its_verdict_from_the_parent(self):
		heat = frappe.get_doc(
			{
				"doctype": "Heat Record",
				"heat_no": f"_KT-HT-CHILD-{frappe.generate_hash(length=4).upper()}",
				"heat_date": nowdate(),
				"spectro_readings": [
					{"element": "C", "value_pct": 3.4, "spec_min": 3.2, "spec_max": 3.6},
					{"element": "S", "value_pct": 0.30, "spec_min": 0, "spec_max": 0.12},
				],
			}
		).insert(ignore_permissions=True)

		# within_spec is read-only on the form - the parent decides it
		self.assertTrue(heat.spectro_readings[0].within_spec)
		self.assertFalse(heat.spectro_readings[1].within_spec)

	def test_test_duty_point_rows_ride_on_the_certificate(self):
		cert = frappe.get_doc(
			{
				"doctype": "Pump Test Certificate",
				"serial_no": fixtures.serial_no(qc_status="Pending"),
				"test_date": now_datetime(),
				"overall_result": "Pass",
				"duty_points": [
					{"head_m": 20, "discharge_lpm": 1100, "efficiency_pct": 48},
					{"head_m": 30, "discharge_lpm": 900, "efficiency_pct": 52, "is_duty_point": 1},
				],
			}
		).insert(ignore_permissions=True)

		reloaded = frappe.get_doc("Pump Test Certificate", cert.name)
		self.assertEqual(len(reloaded.duty_points), 2)
		self.assertEqual([r.is_duty_point for r in reloaded.duty_points], [0, 1])

	def test_service_part_used_prices_itself(self):
		request = fixtures.service_request(submit=True)
		visit = frappe.get_doc(
			{
				"doctype": "Service Visit",
				"service_request": request.name,
				"technician": fixtures.technician(),
				"visit_date": nowdate(),
				"is_chargeable": 1,
				"parts_used": [{"item_code": fixtures.spare_item(), "qty": 3, "rate": 120}],
			}
		).insert(ignore_permissions=True)

		row = visit.parts_used[0]
		self.assertEqual(row.amount, 360)
		self.assertEqual(row.item_name, fixtures.SPARE_ITEM)
		self.assertEqual(row.uom, "Nos")

	def test_claim_part_row_prices_itself(self):
		claim = frappe.get_doc(
			{
				"doctype": "Kumar Warranty Claim",
				"serial_no": fixtures.serial_no(),
				"dealer": fixtures.dealer(),
				"claim_date": nowdate(),
				"defective_parts": [
					{"item_code": fixtures.spare_item(), "qty": 2},
					{"item_code": fixtures.spare_item(), "qty": 1, "rate": 900},
				],
			}
		).insert(ignore_permissions=True)

		# the first row takes the item's valuation rate, the second keeps its own
		self.assertEqual(claim.defective_parts[0].rate, 250)
		self.assertEqual(claim.defective_parts[0].amount, 500)
		self.assertEqual(claim.defective_parts[1].amount, 900)
		self.assertEqual(claim.claim_amount, 1400)
