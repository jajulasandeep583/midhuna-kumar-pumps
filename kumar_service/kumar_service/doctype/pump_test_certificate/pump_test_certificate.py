import frappe
from frappe import _
from frappe.model.document import Document

QC_BY_RESULT = {"Pass": "Passed", "Fail": "Failed", "Rework": "Rework"}


class PumpTestCertificate(Document):
	def validate(self):
		model = frappe.db.get_value("Serial No", self.serial_no, "custom_pump_model")
		if not model:
			frappe.throw(_("Serial number {0} does not exist").format(self.serial_no))
		self.pump_model = model

		if not self.bis_standard_ref:
			self.bis_standard_ref = frappe.db.get_value("Pump Model", model, "bis_standard")

		# a unit cannot pass overall if a sub-test failed
		failed = [
			label
			for label, value in (
				(_("HiPot"), self.hipot_result),
				(_("Hydrostatic"), self.hydrostatic_result),
			)
			if value == "Fail"
		]
		if failed and self.overall_result == "Pass":
			frappe.throw(
				_("Cannot pass this unit: {0} test failed").format(", ".join(failed)),
				title=_("Inconsistent Result"),
			)

	def on_submit(self):
		frappe.db.set_value(
			"Serial No",
			self.serial_no,
			{
				"custom_test_certificate": self.name,
				"custom_qc_status": QC_BY_RESULT.get(self.overall_result, "Pending"),
			},
			update_modified=False,
		)

	def on_cancel(self):
		frappe.db.set_value(
			"Serial No",
			self.serial_no,
			{"custom_test_certificate": None, "custom_qc_status": "Pending"},
			update_modified=False,
		)
