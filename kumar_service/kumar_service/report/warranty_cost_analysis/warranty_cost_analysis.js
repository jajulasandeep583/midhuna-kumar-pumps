frappe.query_reports["Warranty Cost Analysis"] = {
	"filters": [
 {
  "default": "frappe.datetime.add_months(frappe.datetime.get_today(), -3)",
  "fieldname": "from_date",
  "fieldtype": "Date",
  "label": "From Date"
 },
 {
  "default": "frappe.datetime.get_today()",
  "fieldname": "to_date",
  "fieldtype": "Date",
  "label": "To Date"
 }
]
};
