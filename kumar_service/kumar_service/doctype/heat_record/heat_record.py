import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

CASING_ITEM = "KC-CASING"


class HeatRecord(Document):
	def validate(self):
		self.check_spec()
		self.compute_carbon_equivalent()
		self.gate_approval()

	def check_spec(self):
		all_ok = True
		for row in self.spectro_readings:
			within = True
			if row.spec_min is not None and flt(row.value_pct) < flt(row.spec_min):
				within = False
			if row.spec_max is not None and flt(row.value_pct) > flt(row.spec_max):
				within = False
			row.within_spec = 1 if within else 0
			if not within:
				all_ok = False
		self.all_within_spec = 1 if (all_ok and self.spectro_readings) else 0

	def compute_carbon_equivalent(self):
		"""CE = C + (Si + P) / 3 - the number the foundry actually judges a melt on."""
		values = {r.element: flt(r.value_pct) for r in self.spectro_readings}
		if "C" in values:
			self.carbon_equivalent = flt(
				values.get("C", 0) + (values.get("Si", 0) + values.get("P", 0)) / 3.0, 3
			)

	def gate_approval(self):
		if self.status != "Approved for Pouring":
			return

		if not self.spectro_readings:
			frappe.throw(_("Enter the spectrometer readings before approving this heat for pouring"))

		if not self.all_within_spec and not self.override_reason:
			out = [r.element for r in self.spectro_readings if not r.within_spec]
			frappe.throw(
				_("These elements are out of spec: {0}. A Quality Engineer must record an override reason to approve anyway.").format(
					", ".join(out)
				),
				title=_("Chemistry Out of Spec"),
			)

		if not self.all_within_spec and "Quality Engineer" not in frappe.get_roles():
			frappe.throw(_("Only a Quality Engineer can approve an out-of-spec heat"))

		if not self.lab_approved_by:
			self.lab_approved_by = frappe.session.user
			self.lab_approved_on = now_datetime()

	def on_update(self):
		if self.status == "Approved for Pouring":
			self.ensure_batch()

	def ensure_batch(self):
		"""The heat number becomes a real Batch so castings can carry it."""
		if frappe.db.exists("Batch", self.heat_no):
			return
		if not frappe.db.exists("Item", CASING_ITEM):
			return

		batch = frappe.get_doc(
			{
				"doctype": "Batch",
				"batch_id": self.heat_no,
				"item": CASING_ITEM,
				"custom_batch_type": "Heat",
				"custom_heat_record": self.name,
				"custom_grade": self.grade_achieved or self.target_grade,
				"manufacturing_date": self.heat_date,
			}
		)
		batch.flags.ignore_permissions = True
		batch.insert(ignore_permissions=True)
