# Midhuna KUMAR Pumps

A Frappe/ERPNext v16 app for a pump manufacturer: serial and batch traceability
from the foundry heat to the farmer, brand-owned warranty, a dealer network, and
the management screens that read the whole thing.

Built by **MIDHUNATECH** for KUMAR Pumps (Sri Lakshmi Ganapathi Engineering
Works, Tenali).

---

## What it actually does

### Traceability, heat to customer

A pump is serialised at manufacture and carries its parentage forever. From any
serial you can walk **back** to the foundry heat and the winding batch that made
it, or **forward** to the dealer, the end customer, every complaint and every
warranty claim. That chain is what makes `Batch Defect Analysis` able to say
"34.9% of the 43 units from heat HT-260715-008 failed" instead of "some pumps
are bad".

### Two sale channels, because the paperwork really is different

This is the part most pump ERPs get wrong. A pump reaches the end customer two
ways, and the documents behind them are nothing alike:

| | Who sells | Invoice the customer keeps | In our books? |
|---|---|---|---|
| **Direct** | a KUMAR-owned branch | **ours** | yes |
| **Through a dealer** | an independent firm | **the dealer's own**, on their letterhead and GSTIN | no — we only record its number |

Ownership (`Dealer.is_own_outlet`) decides the channel, and the channel decides
which fields on a `Pump Registration` are real. The dealer portal asks a branch
and an independent shop different questions for the same serial.

**The warranty is ours in both cases.** Months resolve
`Item → Pump Model → Pump Category → Settings`, the fields are read-only *and*
recomputed on every save, and `register_pump` re-derives the channel from the
outlet rather than trusting anything posted — a dealer cannot claim their sale
was on a KUMAR invoice.

### Dealer portal

A mobile-first page at `/dealer-portal` for someone standing in a shop:

- type or scan a serial → the server states the model and **the warranty we will
  honour**, before anything is committed
- fill in only their own invoice and the customer's details
- submit, and hand over the A5 **warranty certificate** with its QR code

The certificate prints the proof-of-purchase invoice *and who issued it* — the
dealer with their GSTIN, or KUMAR.

### Management screens

Seven desk pages built on one whitelisted, date-windowed, dealer-scoped endpoint
each: management dashboard, sales, purchase, daily production, dealer network,
people & payroll, plus `my-business` — a deliberately simpler cockpit for a
dealer, because a dealer does not want head office's ranking tables.

**Dealer Network** carries the channel split, units per day per channel, a top
ten, and a "sold nothing this period" call list with tap-to-dial.

### Also in the box

19 DocTypes, 58 custom fields on stock ERPNext doctypes, 10 reports, 4 print
formats, a public `/warranty-check` that leaks no dealer or customer data, a
purpose-drawn 35-glyph icon set, and row-level dealer isolation derived from a
single `Portal User` field.

---

## Install

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/jajulasandeep583/midhuna-kumar-pumps --branch main
bench --site yoursite install-app kumar_service
```

Requires `erpnext`. `hrms` is optional but the people & payroll screen needs it.

## Build the demo company

Everything is defined in code under `kumar_service/setup/`, so a demo site is
one command:

```bash
bench --site yoursite execute kumar_service.setup.demo_full.build_all
```

Order inside `demo_full` is load-bearing: finance masters → traceability →
people → operations → finance settle. Every builder is idempotent — a re-run
tops up rather than duplicates.

Check it end to end:

```bash
bench --site yoursite execute kumar_service.setup.verify.run
```

That asserts the document chains exist, the money reconciles, both sale channels
carry real invoices, nothing was sold before it was manufactured, every dashboard
endpoint answers, and no icon is misconfigured.

## Regenerate the DocTypes from code

With `developer_mode = 1`:

```bash
bench --site yoursite execute kumar_service.install.build_from_code
```

`setup/doctypes.py` is the source of truth; Frappe exports the JSON back into
the app.

---

## Notes for anyone extending this

- **Desk assets must go through the bundler.** `app_include_css`/`app_include_js`
  point at `kumar.bundle.css` / `kumar.bundle.js`. A raw `/assets/...` path
  carries no content hash and Frappe serves it with a 12-hour max-age, so edits
  silently do not reach the browser.
- **A desk Page must live at `<app>/<module>/page/<name>/`** — inside the module
  folder, or Frappe never syncs it.
- **The desk sidebar draws its glyph from `Workspace Sidebar Item`**, not
  `Workspace.icon`, and Frappe only builds those rows at app-install time.
- **Renaming a workspace leaves its JSON on disk**, and `bench migrate`
  re-imports every workspace file — so a deleted screen comes back unless the
  file goes too.

## License

MIT
