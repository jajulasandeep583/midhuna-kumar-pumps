"""Turn a shop's quality record into the stock entry it implies.

A Heat Record says a melt was poured. A Winding Batch Record says a lot was
wound and passed its tests. Neither of them moves any stock, and that gap is
where the traceability story used to break: the casting appeared in stock by
Material Receipt, out of nothing, while the pig iron it was supposedly made from
sat in Stores for ever.

This module is the missing step, and it is deliberately ONE implementation used
from two places - the button on each record, and the demo cycle - so what a
demonstration shows is what an operator would actually get.

What it does is a one-way conversion. The charge goes OUT of Stores and does not
come back; what comes back IN is a different item carrying a Batch whose id IS
the record's number. That batch id is the only "transfer" there is: the metal is
destroyed, and its identity survives as a batch, which is how a heat eventually
reaches a pump's serial number.
"""

import frappe
from frappe import _
from frappe.utils import flt

CASING_ITEM = "KC-CASING"
STATOR_ITEM = "KC-STATOR"

MELT_TYPE = "Foundry Melt"
WINDING_TYPE = "Winding Output"

# A plain grey-iron charge: pig iron for clean carbon, CI scrap (returns plus
# bought scrap) for economy, and the two ferro-alloys that pull silicon and
# manganese up into the FG 200 window the spectro then has to confirm. The
# weights are for a CHARGE_WEIGHT heat and are scaled to whatever the Heat
# Record actually says was charged.
CHARGE_KG = (
	("KR-PIGIRON", 660.0),
	("KR-SCRAP", 500.0),
	("KR-FESI", 24.0),
	("KR-FEMN", 16.0),
)
MOULDING_KG = (("KR-SANDBINDER", 45.0),)
CHARGE_WEIGHT = 1200.0
# ~10 kg of metal per casing. Deliberately far more than one work order uses: a
# heat pours into many moulds, which is exactly why a bad one is worth tracing.
CASTINGS_PER_HEAT = 120

# What one stator is wound from. The copper is nearly all of its value.
WINDING_PER_STATOR = (
	("KR-COPPERWIRE", 1.40),
	("KR-INSULATION", 0.15),
	("KR-VARNISH", 0.18),
)


def company_and_abbr():
	company = (
		frappe.defaults.get_user_default("Company")
		or frappe.defaults.get_global_default("company")
		or frappe.db.get_value("Company", {}, "name")
	)
	if not company:
		frappe.throw(_("No Company on this site"))
	return company, frappe.db.get_value("Company", company, "abbr")


def _wh(abbr, name):
	return f"{name} - {abbr}"


def _entry_type(preferred, fallback):
	return preferred if frappe.db.exists("Stock Entry Type", preferred) else fallback


def _refuse_if_already_made(field, value, entry_type, record):
	existing = frappe.db.get_value(
		"Stock Entry", {field: value, "stock_entry_type": entry_type, "docstatus": ["<", 2]}, "name"
	)
	if existing:
		frappe.throw(
			_("{0} already has a stock entry: {1}").format(
				record, f'<a href="/desk/stock-entry/{existing}">{existing}</a>'
			),
			title=_("Already Posted"),
		)


def _check_stock(consumed, warehouse):
	"""Fail with the shortage named, not with a negative-stock error.

	An operator who is short of pig iron should be told that, on the record they
	pressed the button on - not handed ERPNext's message about a bin.
	"""
	short = []
	for item, qty in consumed:
		available = flt(
			frappe.db.get_value("Bin", {"item_code": item, "warehouse": warehouse}, "actual_qty")
		)
		if available < qty:
			name = frappe.db.get_value("Item", item, "item_name") or item
			short.append(f"<li><b>{name}</b>: need {qty:g}, have {available:g}</li>")
	if short:
		frappe.throw(
			_("Not enough material in {0}:<ul>{1}</ul>Buy it in before posting this entry.").format(
				warehouse, "".join(short)
			),
			title=_("Short of Material"),
		)


def _make_entry(entry_type, consumed, produced_item, produced_qty, batch, source, target, stamp,
		posting_date=None, submit=False):
	company, _abbr = company_and_abbr()
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = entry_type
	se.company = company
	se.fg_completed_qty = produced_qty
	se.update(stamp)
	if posting_date:
		se.posting_date = posting_date
		se.set_posting_time = 1
	for item, qty in consumed:
		se.append("items", {"item_code": item, "qty": qty, "s_warehouse": source})
	# no basic_rate on the output: what the charge cost IS what it costs, and
	# letting ERPNext divide it is the only way the two sides stay honest
	se.append("items", {
		"item_code": produced_item,
		"qty": produced_qty,
		"t_warehouse": target,
		"is_finished_item": 1,
		"use_serial_batch_fields": 1,
		"batch_no": batch,
	})
	se.flags.ignore_permissions = True
	se.insert(ignore_permissions=True)
	if submit:
		se.submit()
	return se


def build_melt_entry(heat_record, posting_date=None, submit=False):
	"""Issue the charge, receive the castings under the heat's own batch."""
	heat = frappe.get_doc("Heat Record", heat_record)
	if heat.status != "Approved for Pouring":
		frappe.throw(
			_("This heat is {0}. Only a heat approved for pouring can be poured.").format(heat.status),
			title=_("Not Approved"),
		)
	_refuse_if_already_made("custom_heat_no", heat.heat_no, _entry_type(MELT_TYPE, "Manufacture"),
		_("Heat {0}").format(heat.heat_no))

	heat.ensure_batch()

	# scale the standard charge to what this heat actually says it melted
	factor = (flt(heat.charge_weight_kg) / CHARGE_WEIGHT) if flt(heat.charge_weight_kg) else 1.0
	consumed = [(item, flt(kg * factor, 3)) for item, kg in CHARGE_KG + MOULDING_KG]
	castings = int(round(CASTINGS_PER_HEAT * factor)) or 1

	_company, abbr = company_and_abbr()
	source = _wh(abbr, "Stores")
	_check_stock(consumed, source)

	return _make_entry(
		entry_type=_entry_type(MELT_TYPE, "Manufacture"),
		consumed=consumed,
		produced_item=CASING_ITEM,
		produced_qty=castings,
		batch=heat.heat_no,
		source=source,
		target=_wh(abbr, "Foundry WIP"),
		stamp={"custom_heat_no": heat.heat_no},
		posting_date=posting_date or heat.heat_date,
		submit=submit,
	)


def build_winding_entry(winding_record, posting_date=None, submit=False):
	"""Issue copper, insulation and varnish; receive the stators that passed."""
	wind = frappe.get_doc("Winding Batch Record", winding_record)
	lot = int(flt(wind.qty_passed) or flt(wind.qty_produced) or 0)
	if lot <= 0:
		frappe.throw(
			_("This lot has no passed quantity, so there is nothing to put into stock."),
			title=_("Nothing Wound"),
		)
	_refuse_if_already_made("custom_winding_batch", wind.batch_no,
		_entry_type(WINDING_TYPE, "Manufacture"), _("Winding lot {0}").format(wind.batch_no))

	ensure_winding_batch(wind)

	consumed = [(item, flt(per * lot, 3)) for item, per in WINDING_PER_STATOR]
	_company, abbr = company_and_abbr()
	source = _wh(abbr, "Stores")
	_check_stock(consumed, source)

	return _make_entry(
		entry_type=_entry_type(WINDING_TYPE, "Manufacture"),
		consumed=consumed,
		produced_item=STATOR_ITEM,
		produced_qty=lot,
		batch=wind.batch_no,
		source=source,
		target=_wh(abbr, "Winding WIP"),
		stamp={"custom_winding_batch": wind.batch_no},
		posting_date=posting_date or wind.winding_date,
		submit=submit,
	)


def ensure_winding_batch(wind):
	"""The winding lot number becomes a real Batch, as the heat number does.

	Heat Record does this for itself on approval; Winding Batch Record has no
	approval step, so it happens here at the point the stock is actually made.
	"""
	if not wind.batch_no or frappe.db.exists("Batch", wind.batch_no):
		return
	if not frappe.db.exists("Item", STATOR_ITEM):
		return
	batch = frappe.get_doc({
		"doctype": "Batch",
		"batch_id": wind.batch_no,
		"item": STATOR_ITEM,
		"custom_batch_type": "Winding",
		"manufacturing_date": wind.winding_date,
	})
	if frappe.get_meta("Batch").has_field("custom_winding_record"):
		batch.custom_winding_record = wind.name
	batch.flags.ignore_permissions = True
	batch.insert(ignore_permissions=True)


# ------------------------------------------------------------------ desk hooks


@frappe.whitelist()
def make_melt_entry(heat_record):
	"""Draft, not submitted: the operator should see the document before posting."""
	frappe.has_permission("Stock Entry", "create", throw=True)
	return build_melt_entry(heat_record).name


@frappe.whitelist()
def make_winding_entry(winding_record):
	frappe.has_permission("Stock Entry", "create", throw=True)
	return build_winding_entry(winding_record).name
