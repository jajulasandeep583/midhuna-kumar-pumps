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
  // An expression, NOT a string: quoted, frappe hands the literal text
  // "frappe.datetime.add_months(...)" to the date control, which cannot parse
  // it and opens the report on a junk date with "must be in format dd-mm-yyyy".
  default: frappe.datetime.add_months(frappe.datetime.get_today(), -3),
  fieldname: "from_date",
  fieldtype: "Date",
  label: "Raised From Date",
 },
 {
  default: frappe.datetime.get_today(),
  fieldname: "to_date",
  fieldtype: "Date",
  label: "Raised To Date",
 }
]
};
