frappe.query_reports["Dealer Performance"] = {
	"filters": [
 {
  "fieldname": "dealer_type",
  "fieldtype": "Select",
  "label": "Dealer Type",
  "options": "\nBranch Office\nAuthorised Distributor\nDealer\nSub-Dealer\nService Centre"
 },
 {
  "fieldname": "state",
  "fieldtype": "Data",
  "label": "State"
 }
]
};
