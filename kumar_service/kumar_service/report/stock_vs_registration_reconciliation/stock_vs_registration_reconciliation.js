frappe.query_reports["Stock vs Registration Reconciliation"] = {
	"filters": [
 {
  "fieldname": "verdict",
  "fieldtype": "Select",
  "label": "Verdict",
  "options": "\nSHIPPED - NOT REGISTERED\nNo stock record at all\nHeld - QC not passed\nIn stock - not sold yet\nRegistered"
 },
 {
  "fieldname": "pump_model",
  "fieldtype": "Link",
  "label": "Pump Model",
  "options": "Pump Model"
 },
 {
  "fieldname": "item_code",
  "fieldtype": "Link",
  "label": "Item",
  "options": "Item"
 },
 {
  "fieldname": "from_date",
  "fieldtype": "Date",
  "label": "Built From"
 },
 {
  "fieldname": "to_date",
  "fieldtype": "Date",
  "label": "Built To"
 },
 {
  "default": 0,
  "fieldname": "include_settled",
  "fieldtype": "Check",
  "label": "Include Already Registered"
 }
]
};
