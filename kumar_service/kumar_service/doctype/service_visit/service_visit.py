import frappe
from frappe.model.document import Document
from frappe.utils import flt


class ServiceVisit(Document):
	def validate(self):
		self.pull_from_request()
		self.compute_totals()

	def pull_from_request(self):
		if not self.service_request:
			return
		sr = frappe.db.get_value(
			"Service Request",
			self.service_request,
			["serial_no", "is_under_warranty", "assigned_technician"],
			as_dict=True,
		)
		if not sr:
			return
		self.serial_no = sr.serial_no
		if not self.technician:
			self.technician = sr.assigned_technician
		if self.is_chargeable is None:
			self.is_chargeable = 0 if sr.is_under_warranty else 1

	def compute_totals(self):
		total = 0.0
		for row in self.parts_used:
			if row.item_code and not row.item_name:
				row.item_name = frappe.db.get_value("Item", row.item_code, "item_name")
			if row.item_code and not row.uom:
				row.uom = frappe.db.get_value("Item", row.item_code, "stock_uom")
			row.amount = flt(row.qty) * flt(row.rate)
			# a warranty replacement is not billed to the customer
			if not row.is_warranty_replacement:
				total += row.amount

		self.total_parts_value = total
		self.grand_total = (total + flt(self.labour_charge)) if self.is_chargeable else 0.0

	def on_submit(self):
		if self.service_request:
			frappe.db.set_value(
				"Service Request", self.service_request, "status", "In Progress", update_modified=False
			)
