"""Build the whole demo company, in the only order that works.

    bench --site kumar.local execute kumar_service.setup.demo_full.build_all

Order is not cosmetic:

  1. finance masters  - GST accounts, tax templates, cost centres and payment
                        terms must exist before an order can carry them
  2. traceability     - heats, windings, serials, warranty, complaints
  3. people           - employees exist before Work Orders name a supervisor
  4. operations       - purchase, BOMs, production, sales
  5. finance settle   - money against the invoices, then the overheads, which
                        read the salary slips written in step 3

Every step is idempotent, so re-running tops up rather than duplicates.
"""

import frappe


def build_all():
	frappe.flags.mute_emails = True
	frappe.flags.in_import = True

	from kumar_service.setup import demo, demo_finance, demo_hr, demo_ops

	print("\n=== 1/5  finance masters")
	demo_finance.masters()

	print("\n=== 2/5  traceability and warranty")
	demo.build_all()

	print("\n=== 3/5  people and payroll")
	demo_hr.build_all()

	print("\n=== 4/5  purchase, production and sales")
	demo_ops.build_all()

	print("\n=== 5/5  payments and overheads")
	demo_finance.settle()

	frappe.db.commit()
	print("\nFULL DEMO COMPANY BUILT")


def ops_only():
	"""Everything except the traceability layer demo.py already built."""
	frappe.flags.mute_emails = True

	from kumar_service.setup import demo_finance, demo_hr, demo_ops

	print("\n=== finance masters")
	demo_finance.masters()
	print("\n=== people and payroll")
	demo_hr.build_all()
	print("\n=== purchase, production and sales")
	demo_ops.build_all()
	print("\n=== payments and overheads")
	demo_finance.settle()

	frappe.db.commit()
	print("\nOPS, HR AND FINANCE BUILT")
