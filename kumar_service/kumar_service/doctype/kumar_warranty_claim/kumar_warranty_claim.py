import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate


class KumarWarrantyClaim(Document):
	def validate(self):
		self.pull_traceability()
		self.compute_amount()

	def pull_traceability(self):
		"""Heat and winding batch ride along on the claim - that is what makes
		batch defect analysis possible later."""
		sn = frappe.db.get_value(
			"Serial No",
			self.serial_no,
			["custom_pump_model", "custom_heat_no", "custom_winding_batch", "custom_dealer"],
			as_dict=True,
		)
		if not sn:
			frappe.throw(_("Serial number {0} does not exist").format(self.serial_no))

		self.pump_model = sn.custom_pump_model
		self.heat_no = sn.custom_heat_no
		self.winding_batch = sn.custom_winding_batch
		if not self.dealer:
			self.dealer = sn.custom_dealer

	def compute_amount(self):
		total = 0.0
		for row in self.defective_parts:
			if row.item_code and not row.item_name:
				row.item_name = frappe.db.get_value("Item", row.item_code, "item_name")
			if row.item_code and not row.rate:
				row.rate = frappe.db.get_value("Item", row.item_code, "valuation_rate") or 0
			row.amount = flt(row.qty) * flt(row.rate)
			total += row.amount
		self.claim_amount = total

	def on_submit(self):
		if self.service_request:
			frappe.db.set_value(
				"Service Request", self.service_request, "linked_claim", self.name, update_modified=False
			)

	def on_update_after_submit(self):
		if self.workflow_state == "Settled" and not self.settled_on:
			self.db_set("settled_on", nowdate(), update_modified=False)

	def on_cancel(self):
		if self.service_request:
			frappe.db.set_value(
				"Service Request", self.service_request, "linked_claim", None, update_modified=False
			)
