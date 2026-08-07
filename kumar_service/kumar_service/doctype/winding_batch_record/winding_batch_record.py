import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

STATOR_ITEM = "KC-STATOR"


class WindingBatchRecord(Document):
	def validate(self):
		produced = cint(self.qty_produced)
		passed = cint(self.qty_passed)
		rejected = cint(self.qty_rejected)

		if passed + rejected > produced:
			frappe.throw(_("Passed + rejected ({0}) cannot exceed the quantity produced ({1})").format(
				passed + rejected, produced
			))

		if produced and not passed and not rejected:
			self.qty_passed = produced

		if rejected and not self.rejection_reason:
			frappe.throw(_("Record why {0} stators were rejected").format(rejected))

	def on_update(self):
		self.ensure_batch()

	def ensure_batch(self):
		if frappe.db.exists("Batch", self.batch_no):
			return
		if not frappe.db.exists("Item", STATOR_ITEM):
			return

		batch = frappe.get_doc(
			{
				"doctype": "Batch",
				"batch_id": self.batch_no,
				"item": STATOR_ITEM,
				"custom_batch_type": "Winding",
				"manufacturing_date": self.winding_date,
			}
		)
		batch.flags.ignore_permissions = True
		batch.insert(ignore_permissions=True)
