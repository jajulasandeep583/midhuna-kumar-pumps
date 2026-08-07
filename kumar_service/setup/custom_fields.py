"""Custom fields on standard ERPNext DocTypes.

The spec is explicit: extend ERPNext, don't rebuild it. Serial No is the
traceability spine, so most of the weight sits there.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

QC_STATUSES = "Pending\nPassed\nFailed\nRework"
# Which side of the business a sale is. Carried on the order, the delivery and
# the invoice alike, so every standard ERPNext report can split "sold into the
# dealer network" from "sold over our own counter" - two businesses with
# different margins that otherwise add up into one meaningless number.
SALE_CHANNEL_OPTIONS = "\nTrade - Sold to Dealer\nDirect - Sold to End Customer"
WARRANTY_STATUSES = "Not Registered\nIn Warranty\nExpiring Soon\nExpired\nVoid"
TRACE_GROUPS = "\nCasing\nStator\nRotor\nImpeller\nShaft\nBought-out\nNA"

CUSTOM_FIELDS = {
	"Item": [
		{
			"fieldname": "custom_kumar_sb",
			"label": "KUMAR Pump Details",
			"fieldtype": "Section Break",
			"insert_after": "item_group",
			"collapsible": 1,
		},
		{
			"fieldname": "custom_pump_model",
			"label": "Pump Model",
			"fieldtype": "Link",
			"options": "Pump Model",
			"insert_after": "custom_kumar_sb",
		},
		{
			"fieldname": "custom_pump_category",
			"label": "Pump Category",
			"fieldtype": "Link",
			"options": "Pump Category",
			"fetch_from": "custom_pump_model.pump_category",
			"read_only": 1,
			"insert_after": "custom_pump_model",
		},
		{
			"fieldname": "custom_is_finished_pump",
			"label": "Is Finished Pump",
			"fieldtype": "Check",
			"insert_after": "custom_pump_category",
			"description": "Drives serial enforcement and QC gating",
		},
		{"fieldname": "custom_kumar_cb", "fieldtype": "Column Break", "insert_after": "custom_is_finished_pump"},
		{
			"fieldname": "custom_warranty_months",
			"label": "Warranty (Months)",
			"fieldtype": "Int",
			"insert_after": "custom_kumar_cb",
			"description": "Overrides the model default",
		},
		{
			"fieldname": "custom_bis_standard",
			"label": "BIS Standard",
			"fieldtype": "Data",
			"insert_after": "custom_warranty_months",
		},
		{
			"fieldname": "custom_trace_group",
			"label": "Traceability Group",
			"fieldtype": "Select",
			"options": TRACE_GROUPS,
			"insert_after": "custom_bis_standard",
			"description": "Which genealogy slot a consumed component fills",
		},
	],
	"Serial No": [
		{
			"fieldname": "custom_identity_sb",
			"label": "Pump Identity",
			"fieldtype": "Section Break",
			"insert_after": "item_code",
		},
		{
			"fieldname": "custom_pump_model",
			"label": "Pump Model",
			"fieldtype": "Link",
			"options": "Pump Model",
			"insert_after": "custom_identity_sb",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "custom_manufacturing_date",
			"label": "Manufacturing Date",
			"fieldtype": "Date",
			"insert_after": "custom_pump_model",
		},
		{
			"fieldname": "custom_work_order",
			"label": "Work Order",
			"fieldtype": "Link",
			"options": "Work Order",
			"insert_after": "custom_manufacturing_date",
		},
		{"fieldname": "custom_identity_cb", "fieldtype": "Column Break", "insert_after": "custom_work_order"},
		{
			"fieldname": "custom_qc_status",
			"label": "QC Status",
			"fieldtype": "Select",
			"options": QC_STATUSES,
			"default": "Pending",
			"insert_after": "custom_identity_cb",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "custom_test_certificate",
			"label": "Test Certificate",
			"fieldtype": "Link",
			"options": "Pump Test Certificate",
			"read_only": 1,
			"insert_after": "custom_qc_status",
		},
		{
			"fieldname": "custom_qr_url",
			"label": "QR URL",
			"fieldtype": "Data",
			"read_only": 1,
			"insert_after": "custom_test_certificate",
		},
		{
			"fieldname": "custom_genealogy_sb",
			"label": "Genealogy",
			"fieldtype": "Section Break",
			"insert_after": "custom_qr_url",
		},
		{
			"fieldname": "custom_heat_no",
			"label": "Casing Heat No",
			"fieldtype": "Link",
			"options": "Batch",
			"read_only": 1,
			"insert_after": "custom_genealogy_sb",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "custom_winding_batch",
			"label": "Winding Batch",
			"fieldtype": "Link",
			"options": "Batch",
			"read_only": 1,
			"insert_after": "custom_heat_no",
		},
		{"fieldname": "custom_genealogy_cb", "fieldtype": "Column Break", "insert_after": "custom_winding_batch"},
		{
			"fieldname": "custom_rotor_batch",
			"label": "Rotor Batch",
			"fieldtype": "Link",
			"options": "Batch",
			"read_only": 1,
			"insert_after": "custom_genealogy_cb",
		},
		{
			"fieldname": "custom_warranty_sb",
			"label": "Sale & Warranty",
			"fieldtype": "Section Break",
			"insert_after": "custom_rotor_batch",
		},
		{
			"fieldname": "custom_dealer",
			"label": "Dealer",
			"fieldtype": "Link",
			"options": "Dealer",
			"insert_after": "custom_warranty_sb",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "custom_registration",
			"label": "Registration",
			"fieldtype": "Link",
			"options": "Pump Registration",
			"read_only": 1,
			"insert_after": "custom_dealer",
		},
		{
			"fieldname": "custom_sale_date",
			"label": "Sale Date",
			"fieldtype": "Date",
			"insert_after": "custom_registration",
		},
		{
			"fieldname": "custom_warranty_start_date",
			"label": "Warranty Start",
			"fieldtype": "Date",
			"insert_after": "custom_sale_date",
		},
		{"fieldname": "custom_warranty_cb", "fieldtype": "Column Break", "insert_after": "custom_warranty_start_date"},
		{
			"fieldname": "custom_warranty_expiry_date",
			"label": "Warranty Expiry",
			"fieldtype": "Date",
			"insert_after": "custom_warranty_cb",
			"search_index": 1,
		},
		{
			"fieldname": "custom_warranty_status",
			"label": "Warranty Status",
			"fieldtype": "Select",
			"options": WARRANTY_STATUSES,
			"default": "Not Registered",
			"insert_after": "custom_warranty_expiry_date",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "custom_customer_sb",
			"label": "End Customer",
			"fieldtype": "Section Break",
			"insert_after": "custom_warranty_status",
		},
		{
			"fieldname": "custom_end_customer_name",
			"label": "End Customer Name",
			"fieldtype": "Data",
			"insert_after": "custom_customer_sb",
		},
		{
			"fieldname": "custom_end_customer_mobile",
			"label": "End Customer Mobile",
			"fieldtype": "Data",
			"insert_after": "custom_end_customer_name",
		},
		{"fieldname": "custom_customer_cb", "fieldtype": "Column Break", "insert_after": "custom_end_customer_mobile"},
		{
			"fieldname": "custom_installation_pincode",
			"label": "Installation Pincode",
			"fieldtype": "Data",
			"insert_after": "custom_customer_cb",
		},
	],
	"Stock Entry": [
		{
			"fieldname": "custom_trace_sb",
			"label": "Traceability",
			"fieldtype": "Section Break",
			"insert_after": "purpose",
			"collapsible": 1,
		},
		{
			"fieldname": "custom_heat_no",
			"label": "Heat No",
			"fieldtype": "Link",
			"options": "Batch",
			"insert_after": "custom_trace_sb",
		},
		{
			"fieldname": "custom_shift",
			"label": "Shift",
			"fieldtype": "Select",
			"options": "\nA\nB\nC",
			"insert_after": "custom_heat_no",
		},
		{"fieldname": "custom_trace_cb", "fieldtype": "Column Break", "insert_after": "custom_shift"},
		{
			"fieldname": "custom_operator",
			"label": "Operator",
			"fieldtype": "Link",
			"options": "Employee",
			"insert_after": "custom_trace_cb",
		},
		{
			"fieldname": "custom_traceability_verified",
			"label": "Traceability Verified",
			"fieldtype": "Check",
			"read_only": 1,
			"insert_after": "custom_operator",
		},
	],
	"Work Order": [
		{
			"fieldname": "custom_trace_sb",
			"label": "Traceability",
			"fieldtype": "Section Break",
			"insert_after": "production_item",
			"collapsible": 1,
		},
		{
			"fieldname": "custom_heat_no",
			"label": "Heat No",
			"fieldtype": "Link",
			"options": "Batch",
			"insert_after": "custom_trace_sb",
		},
		{
			"fieldname": "custom_winding_batch",
			"label": "Winding Batch",
			"fieldtype": "Link",
			"options": "Batch",
			"insert_after": "custom_heat_no",
		},
		{"fieldname": "custom_wo_cb", "fieldtype": "Column Break", "insert_after": "custom_winding_batch"},
		{
			"fieldname": "custom_route_card_printed",
			"label": "Route Card Printed",
			"fieldtype": "Check",
			"insert_after": "custom_wo_cb",
		},
	],
	"Batch": [
		{
			"fieldname": "custom_batch_type",
			"label": "Batch Type",
			"fieldtype": "Select",
			"options": "\nHeat\nWinding\nRotor\nPaint\nBought-out",
			"insert_after": "item",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "custom_heat_record",
			"label": "Heat Record",
			"fieldtype": "Link",
			"options": "Heat Record",
			"insert_after": "custom_batch_type",
		},
		{
			"fieldname": "custom_grade",
			"label": "Grade",
			"fieldtype": "Data",
			"insert_after": "custom_heat_record",
			"description": "e.g. FG 200 / FG 260",
		},
	],
	"Sales Invoice": [
		{
			"fieldname": "custom_kumar_sb",
			"label": "KUMAR Dispatch Details",
			"fieldtype": "Section Break",
			"insert_after": "customer_name",
			"collapsible": 1,
		},
		{
			"fieldname": "custom_dealer",
			"label": "Sold By / Billed To Dealer",
			"fieldtype": "Link",
			"options": "Dealer",
			"insert_after": "custom_kumar_sb",
			"description": "On a trade sale this is the dealer we are billing. On a "
			"direct sale it is the KUMAR branch that made the sale.",
		},
		{
			# lets every standard report separate "sold into the network" from
			# "sold to the public", which are different businesses with
			# different margins
			"fieldname": "custom_sale_channel",
			"label": "Sale Channel",
			"fieldtype": "Select",
			"options": SALE_CHANNEL_OPTIONS,
			"insert_after": "custom_dealer",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "custom_dispatch_through",
			"label": "Dispatch Through",
			"fieldtype": "Data",
			"insert_after": "custom_dealer",
		},
		{
			"fieldname": "custom_lr_no",
			"label": "LR / Docket No",
			"fieldtype": "Data",
			"insert_after": "custom_dispatch_through",
		},
		{"fieldname": "custom_kumar_cb", "fieldtype": "Column Break", "insert_after": "custom_lr_no"},
		{
			"fieldname": "custom_vehicle_no",
			"label": "Vehicle No",
			"fieldtype": "Data",
			"insert_after": "custom_kumar_cb",
		},
		{
			"fieldname": "custom_auto_register_pumps",
			"label": "Auto-Register Pumps",
			"fieldtype": "Check",
			"insert_after": "custom_vehicle_no",
			"description": "On submit, create a Pump Registration for every serial sold",
		},
		{
			"fieldname": "custom_warranty_note",
			"label": "Warranty Note",
			"fieldtype": "Small Text",
			"insert_after": "custom_auto_register_pumps",
			"read_only": 1,
		},
	],
	"Delivery Note": [
		{
			"fieldname": "custom_dealer",
			"label": "Sold By / Billed To Dealer",
			"fieldtype": "Link",
			"options": "Dealer",
			"insert_after": "customer_name",
		},
		{
			"fieldname": "custom_sale_channel",
			"label": "Sale Channel",
			"fieldtype": "Select",
			"options": SALE_CHANNEL_OPTIONS,
			"insert_after": "custom_dealer",
		},
	],
	# an order is routed through a dealer just like the invoice and the
	# delivery it turns into - without it the funnel loses the dealer halfway.
	# The channel rides along the same way: it is decided when the order is
	# taken, not rediscovered at invoicing.
	"Sales Order": [
		{
			"fieldname": "custom_dealer",
			"label": "Sold By / Billed To Dealer",
			"fieldtype": "Link",
			"options": "Dealer",
			"insert_after": "customer_name",
		},
		{
			"fieldname": "custom_sale_channel",
			"label": "Sale Channel",
			"fieldtype": "Select",
			"options": SALE_CHANNEL_OPTIONS,
			"insert_after": "custom_dealer",
		},
	],
	"Customer": [
		{
			"fieldname": "custom_dealer",
			"label": "Dealer",
			"fieldtype": "Link",
			"options": "Dealer",
			"insert_after": "customer_group",
		},
	],
	# who actually ran the job - the shop floor board is meaningless without it
	"Work Order": [
		{
			"fieldname": "custom_shift",
			"label": "Shift",
			"fieldtype": "Select",
			"options": "\nA\nB\nC",
			"insert_after": "custom_winding_batch",
		},
		{
			"fieldname": "custom_supervisor",
			"label": "Supervisor",
			"fieldtype": "Link",
			"options": "Employee",
			"insert_after": "custom_shift",
		},
	],
}


def build_all():
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True, update=True)
	for df in frappe.get_all(
		"Custom Field", filters={"dt": ["in", list(CUSTOM_FIELDS)], "fieldname": ["like", "custom_%"]}
	):
		frappe.db.set_value("Custom Field", df.name, "module", "Kumar Service", update_modified=False)
	frappe.db.commit()
