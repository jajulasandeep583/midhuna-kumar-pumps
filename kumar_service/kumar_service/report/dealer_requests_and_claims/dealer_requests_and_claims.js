frappe.query_reports["Dealer Requests and Claims"] = {
	"filters": [
 {
  "fieldname": "kind",
  "fieldtype": "Select",
  "label": "Type",
  "options": "\nComplaint\nWarranty Claim"
 },
 {
  "fieldname": "source",
  "fieldtype": "Select",
  "label": "Raised From",
  "options": "\nPortal\nDesk"
 },
 {
  "fieldname": "dealer",
  "fieldtype": "Link",
  "label": "Dealer (with its network)",
  "options": "Dealer"
 },
 {
  "fieldname": "status",
  "fieldtype": "Data",
  "label": "Status"
 },
 {
  "default": "frappe.datetime.add_months(frappe.datetime.get_today(), -3)",
  "fieldname": "from_date",
  "fieldtype": "Date",
  "label": "Raised From Date"
 },
 {
  "default": "frappe.datetime.get_today()",
  "fieldname": "to_date",
  "fieldtype": "Date",
  "label": "Raised To Date"
 }
]
};
