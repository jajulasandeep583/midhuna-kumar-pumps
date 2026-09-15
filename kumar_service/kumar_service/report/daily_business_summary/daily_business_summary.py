"""Daily Business Summary: the day's sales, purchases and cash on one screen.

Brought over from the Script Report Midhun runs on another site, where it lives
in the database as a server script. Here it ships as a file: this bench has
server scripts switched off, and a database report would only answer "Server
Scripts are disabled". The queries are unchanged.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate


def execute(filters=None):
	filters = filters or {}
	from_date = filters.get("from_date") or nowdate()
	to_date = filters.get("to_date") or nowdate()
	company = filters.get("company") or frappe.defaults.get_user_default("Company") or frappe.db.get_default(
		"Company"
	)

	columns = [
		{"fieldname": "section", "label": _("Section"), "fieldtype": "Data", "width": 450},
		{"fieldname": "count", "label": _("Count"), "fieldtype": "Int", "width": 80},
		{"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 200},
		{"fieldname": "row_type", "label": _("Type"), "fieldtype": "Data", "hidden": 1},
	]

	params = {"fd": from_date, "td": to_date, "co": company}

	# Sales Invoices - a credit note carries a negative total, so summing nets it off
	sales = frappe.db.sql(
		"""
		SELECT
			SUM(CASE WHEN is_return = 0 THEN 1 ELSE 0 END) AS cnt,
			IFNULL(SUM(CASE WHEN is_return = 0 THEN grand_total ELSE 0 END), 0) AS total,
			IFNULL(SUM(base_net_total), 0) AS net_total
		FROM `tabSales Invoice`
		WHERE docstatus = 1
		AND posting_date BETWEEN %(fd)s AND %(td)s
		AND company = %(co)s
		""",
		params,
		as_dict=True,
	)[0]

	# Purchase Invoices - net of debit notes
	purchases = frappe.db.sql(
		"""
		SELECT
			SUM(CASE WHEN is_return = 0 THEN 1 ELSE 0 END) AS cnt,
			IFNULL(SUM(CASE WHEN is_return = 0 THEN grand_total ELSE 0 END), 0) AS total,
			IFNULL(SUM(base_net_total), 0) AS net_total
		FROM `tabPurchase Invoice`
		WHERE docstatus = 1
		AND posting_date BETWEEN %(fd)s AND %(td)s
		AND company = %(co)s
		""",
		params,
		as_dict=True,
	)[0]

	collections = frappe.db.sql(
		"""
		SELECT COUNT(*) AS cnt, IFNULL(SUM(paid_amount), 0) AS total
		FROM `tabPayment Entry`
		WHERE docstatus = 1
		AND payment_type = 'Receive'
		AND posting_date BETWEEN %(fd)s AND %(td)s
		AND company = %(co)s
		""",
		params,
		as_dict=True,
	)[0]

	payments = frappe.db.sql(
		"""
		SELECT COUNT(*) AS cnt, IFNULL(SUM(paid_amount), 0) AS total
		FROM `tabPayment Entry`
		WHERE docstatus = 1
		AND payment_type = 'Pay'
		AND posting_date BETWEEN %(fd)s AND %(td)s
		AND company = %(co)s
		""",
		params,
		as_dict=True,
	)[0]

	# money in and out through bank / cash journals
	je_recv = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT gle.voucher_no) AS cnt,
			IFNULL(SUM(gle.debit), 0) AS total
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		INNER JOIN `tabJournal Entry` je ON je.name = gle.voucher_no
		WHERE gle.voucher_type = 'Journal Entry'
		AND je.voucher_type IN ('Bank Entry', 'Cash Entry')
		AND acc.account_type IN ('Bank', 'Cash')
		AND gle.debit > 0
		AND gle.is_cancelled = 0
		AND gle.posting_date BETWEEN %(fd)s AND %(td)s
		AND gle.company = %(co)s
		""",
		params,
		as_dict=True,
	)[0]

	je_pay = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT gle.voucher_no) AS cnt,
			IFNULL(SUM(gle.credit), 0) AS total
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		INNER JOIN `tabJournal Entry` je ON je.name = gle.voucher_no
		WHERE gle.voucher_type = 'Journal Entry'
		AND je.voucher_type IN ('Bank Entry', 'Cash Entry')
		AND acc.account_type IN ('Bank', 'Cash')
		AND gle.credit > 0
		AND gle.is_cancelled = 0
		AND gle.posting_date BETWEEN %(fd)s AND %(td)s
		AND gle.company = %(co)s
		""",
		params,
		as_dict=True,
	)[0]

	pending_po = frappe.db.sql(
		"""
		SELECT COUNT(*) AS cnt, IFNULL(SUM(grand_total), 0) AS total
		FROM `tabPurchase Order`
		WHERE docstatus = 1
		AND status NOT IN ('Completed', 'Cancelled', 'Closed')
		AND company = %(co)s
		""",
		{"co": company},
		as_dict=True,
	)[0]

	pending_so = frappe.db.sql(
		"""
		SELECT COUNT(*) AS cnt, IFNULL(SUM(grand_total), 0) AS total
		FROM `tabSales Order`
		WHERE docstatus = 1
		AND status NOT IN ('Completed', 'Cancelled', 'Closed')
		AND company = %(co)s
		""",
		{"co": company},
		as_dict=True,
	)[0]

	receivable = frappe.db.sql(
		"""
		SELECT IFNULL(SUM(amount), 0) AS total
		FROM `tabPayment Ledger Entry`
		WHERE party_type = 'Customer'
		AND delinked = 0
		AND posting_date <= %(td)s
		AND company = %(co)s
		""",
		{"td": to_date, "co": company},
		as_dict=True,
	)[0]

	payable = frappe.db.sql(
		"""
		SELECT IFNULL(SUM(amount), 0) AS total
		FROM `tabPayment Ledger Entry`
		WHERE party_type = 'Supplier'
		AND delinked = 0
		AND posting_date <= %(td)s
		AND company = %(co)s
		""",
		{"td": to_date, "co": company},
		as_dict=True,
	)[0]

	# net of tax (base_net_total), which is what Sales Invoice Trends shows
	s = flt(sales.get("net_total"))
	p = flt(purchases.get("net_total"))
	c = flt(collections.get("total"))
	py_ = flt(payments.get("total"))
	jc = flt(je_recv.get("total"))
	jp = flt(je_pay.get("total"))
	net = (c + jc) - (py_ + jp)

	receivable_amt = flt(receivable.get("total"))
	payable_amt = abs(flt(payable.get("total")))

	rows = [
		{"section": _("─── SALES"), "count": None, "amount": None, "row_type": "header"},
		{"section": _("Sales Invoices"), "count": cint(sales.get("cnt")), "amount": s, "row_type": "sales"},
		{"section": _("Sales Orders Pending"), "count": cint(pending_so.get("cnt")),
			"amount": flt(pending_so.get("total")), "row_type": "info_so"},
		{"section": _("Total Receivable"), "count": None, "amount": receivable_amt, "row_type": "total_recv"},

		{"section": _("─── PURCHASES"), "count": None, "amount": None, "row_type": "header"},
		{"section": _("Purchase Invoices"), "count": cint(purchases.get("cnt")), "amount": p,
			"row_type": "purchase"},
		{"section": _("Purchase Orders Pending"), "count": cint(pending_po.get("cnt")),
			"amount": flt(pending_po.get("total")), "row_type": "info_po"},
		{"section": _("Total Payable"), "count": None, "amount": payable_amt, "row_type": "total_pay"},

		{"section": _("─── CASH FLOW"), "count": None, "amount": None, "row_type": "header"},
		{"section": _("Collections (PE)"), "count": cint(collections.get("cnt")), "amount": c,
			"row_type": "collection"},
		{"section": _("Collections (JE)"), "count": cint(je_recv.get("cnt")), "amount": jc,
			"row_type": "je_collection"},
		{"section": _("Payments (PE)"), "count": cint(payments.get("cnt")), "amount": py_, "row_type": "payment"},
		{"section": _("Payments (JE)"), "count": cint(je_pay.get("cnt")), "amount": jp, "row_type": "je_payment"},
		{"section": _("Net Cash Flow"), "count": None, "amount": net, "row_type": "net"},
	]

	report_summary = [
		{"value": s, "label": _("Sales"), "datatype": "Currency", "currency": "INR", "indicator": "green"},
		{"value": p, "label": _("Purchases"), "datatype": "Currency", "currency": "INR", "indicator": "red"},
		{"value": c + jc, "label": _("Collections"), "datatype": "Currency", "currency": "INR",
			"indicator": "green"},
		{"value": py_ + jp, "label": _("Payments"), "datatype": "Currency", "currency": "INR",
			"indicator": "red"},
		{"value": net, "label": _("Net Cash"), "datatype": "Currency", "currency": "INR", "indicator": "blue"},
	]

	return columns, rows, None, None, report_summary
