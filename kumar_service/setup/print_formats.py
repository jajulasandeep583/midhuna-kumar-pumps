"""Print formats. The Warranty Certificate is the one the dealer hands over.

Every label goes through the jinja gettext helper so the same template prints in
English or Telugu - pick the language in the print view's language selector, or
append ``?_lang=te`` to the print URL. The warranty terms are deliberately
printed in BOTH languages on every copy: it is the customer's legal paper and in
Guntur district the person holding it may read only Telugu.
"""

import frappe

MODULE = "Kumar Service"

# Telugu needs a font that actually has the glyphs. Noto Sans Telugu is the
# usual one on a Linux server, Gautami/Nirmala UI on Windows; without them
# wkhtmltopdf silently prints boxes.
FONT_STACK = (
	'"Inter", Arial, "Noto Sans Telugu", "Gautami", "Nirmala UI", '
	'"Lohit Telugu", "Pothana2000", sans-serif'
)

BRAND_CSS = (
	"""
<style>
  .k-wrap { font-family: %s; color:#1a1a1a; }
  .k-head { display:flex; justify-content:space-between; align-items:flex-start;
            border-bottom:3px solid #0b5394; padding-bottom:10px; margin-bottom:14px; }
  .k-brand { font-size:26px; font-weight:800; color:#0b5394; letter-spacing:0.5px; }
  .k-sub { font-size:10px; color:#555; line-height:1.5; }
  .k-title { text-align:center; font-size:16px; font-weight:700; letter-spacing:2px;
             text-transform:uppercase; margin:10px 0 14px; color:#0b5394; }
  .k-grid { width:100%%; border-collapse:collapse; margin-bottom:12px; }
  .k-grid td { border:1px solid #cfd8e3; padding:6px 9px; font-size:11px; vertical-align:top; }
  .k-grid td.k-label { background:#f2f6fb; font-weight:600; width:26%%; color:#33475b; }
  .k-badge { display:inline-block; padding:5px 14px; border-radius:20px; font-weight:700;
             font-size:12px; letter-spacing:0.5px; }
  .k-ok { background:#e6f4ea; color:#137333; border:1px solid #137333; }
  .k-no { background:#fce8e6; color:#a50e0e; border:1px solid #a50e0e; }
  .k-foot { margin-top:18px; font-size:9px; color:#666; line-height:1.6;
            border-top:1px solid #cfd8e3; padding-top:8px; }
  .k-sign { margin-top:26px; display:flex; justify-content:space-between; font-size:10px; }
  .k-sign div { width:30%%; border-top:1px solid #333; padding-top:4px; text-align:center; }
  .k-qr { text-align:center; }
  .k-qr img { width:110px; height:110px; }
  /* A Telugu label is taller and wider than its English original; give the
     label column a little more room so a two-word label does not wrap to
     three lines and push an A5 card onto a second page. */
  .k-te .k-grid td.k-label { width:30%%; }
  .k-te .k-title { letter-spacing:0.5px; }
</style>
"""
	% FONT_STACK
)

# `frappe.lang` is the only reliable place to read the print language from - the
# print format template is rendered with its own args and does NOT get the
# printview page's `lang`.
WRAP_OPEN = '<div class="k-wrap{% if frappe.lang and frappe.lang.startswith("te") %} k-te{% endif %}">'

HEADER = """
<div class="k-head">
  <div>
    <div class="k-brand">KUMAR</div>
    <div class="k-sub">
      <b>{{ _("Sri Lakshmi Ganapathi Engineering Works") }}</b><br>
      {{ _("Pumps &amp; Motors") }} &middot; ISO 9001:2015<br>
      {{ _("Plot 9-14 &amp; 17-24, Industrial Estate, Sultanabad,") }}<br>
      {{ _("Tenali - 522202, Guntur Dist., Andhra Pradesh") }}
    </div>
  </div>
  <div class="k-sub" style="text-align:right">
    {{ _("Since 1971") }}<br>
    {{ frappe.utils.format_date(frappe.utils.nowdate()) }}
  </div>
</div>
"""

WARRANTY_CARD = (
	BRAND_CSS
	+ WRAP_OPEN
	+ HEADER
	+ """
<div class="k-title">{{ _("Warranty Certificate") }}</div>

<table class="k-grid">
  <tr>
    <td class="k-label">{{ _("Certificate No") }}</td><td><b>{{ doc.warranty_card_no or doc.name }}</b></td>
    <td class="k-label">{{ _("Registration") }}</td><td>{{ doc.name }}</td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Serial Number") }}</td><td><b style="font-size:13px">{{ doc.serial_no }}</b></td>
    <td class="k-label">{{ _("Model") }}</td><td><b>{{ doc.pump_model or "" }}</b></td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Rating") }}</td><td>{{ doc.hp or "" }} {{ _("HP") }} &middot; {{ _(doc.phase) if doc.phase else "" }}</td>
    <td class="k-label">{{ _("Manufactured On") }}</td><td>{{ frappe.utils.format_date(doc.manufacturing_date) }}</td>
  </tr>
</table>

<table class="k-grid">
  <tr>
    <td class="k-label">{{ _("Customer") }}</td><td><b>{{ doc.end_customer_name }}</b></td>
    <td class="k-label">{{ _("Mobile") }}</td><td>{{ doc.end_customer_mobile }}</td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Installed At") }}</td>
    <td colspan="3">{{ doc.installation_address or "" }}{% if doc.district %}, {{ doc.district }}{% endif %}{% if doc.state %}, {{ doc.state }}{% endif %} {{ doc.pincode or "" }}</td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Application") }}</td><td>{{ _(doc.application_type) if doc.application_type else "" }}</td>
    <td class="k-label">{{ _("Sold By") }}</td><td>{{ doc.dealer }}</td>
  </tr>
  {# The customer's proof of purchase, and it is not the same document in both
     cases: through a dealer it is the DEALER's bill, on their GSTIN; over our
     own counter it is ours. A claim is settled against whichever this says. #}
  <tr>
    {# Not "Purchase Invoice": that string is also the ERPNext DocType label on
       the workspaces, and the two do not translate the same way. #}
    <td class="k-label">{{ _("Proof of Purchase") }}</td>
    <td>
      {%- if doc.sales_invoice -%}
        <b>{{ doc.sales_invoice }}</b>
      {%- else -%}
        <b>{{ doc.invoice_no or "-" }}</b>
        {%- if doc.dealer_invoice_date %} &middot; {{ frappe.utils.format_date(doc.dealer_invoice_date) }}{% endif -%}
      {%- endif -%}
    </td>
    <td class="k-label">{{ _("Invoice Issued By") }}</td>
    <td>
      {%- if doc.sales_invoice -%}
        {{ _("KUMAR Pumps &amp; Motors") }}
      {%- else -%}
        {{ doc.dealer }}{% if doc.dealer_gstin %}<br><span class="k-sub">{{ _("GSTIN") }} {{ doc.dealer_gstin }}</span>{% endif %}
      {%- endif -%}
    </td>
  </tr>
</table>

<table class="k-grid">
  <tr>
    <td class="k-label">{{ _("Date of Sale") }}</td><td><b>{{ frappe.utils.format_date(doc.sale_date) }}</b></td>
    <td class="k-label">{{ _("Warranty Period") }}</td>
    <td><b>{{ doc.warranty_months }} {{ _("months") }}</b></td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Valid From") }}</td><td>{{ frappe.utils.format_date(doc.warranty_start_date) }}</td>
    <td class="k-label">{{ _("Valid Upto") }}</td>
    <td><span class="k-badge k-ok">{{ frappe.utils.format_date(doc.warranty_expiry_date) }}</span></td>
  </tr>
</table>

<div class="k-qr">
  {% set img = qr_base64(doc.qr_url or qr_url_for(doc.serial_no)) %}
  {% if img %}<img src="{{ img }}">{% endif %}
  <div class="k-sub">{{ _("Scan to verify warranty status") }}<br>{{ doc.qr_url }}</div>
</div>

<div class="k-sign">
  <div>{{ _("Customer Signature") }}</div>
  <div>{{ _("Dealer Stamp &amp; Signature") }}</div>
  <div>{{ _("For KUMAR Pumps &amp; Motors") }}</div>
</div>

{# Terms print in both languages on every copy, whatever the print language. #}
<div class="k-foot">
  <b>Terms:</b> This warranty covers manufacturing defects only, for the period stated above from the
  date of sale. It does not cover damage from voltage fluctuation beyond rated limits, dry running,
  sand or abrasive water, incorrect installation, unauthorised repair, or normal wear of consumable
  parts such as seals and bearings. The defective unit must be produced with this certificate.
  Warranty is void if the serial number is defaced or altered. Issued on behalf of
  <b>KUMAR Pumps &amp; Motors</b>, a brand of Sri Lakshmi Ganapathi Engineering Works.<br><br>
  <b>వారంటీ నిబంధనలు:</b> ఈ వారంటీ కేవలం తయారీ లోపాలకు మాత్రమే వర్తిస్తుంది. తప్పు ఇన్‌స్టాలేషన్,
  వోల్టేజ్ హెచ్చుతగ్గులు, డ్రై రన్నింగ్, ఇసుకతో కూడిన నీరు లేదా అనధికార మరమ్మతుల వల్ల కలిగే
  నష్టానికి వర్తించదు. సీల్స్, బేరింగ్‌ల వంటి అరిగిపోయే భాగాల సాధారణ అరుగుదల వారంటీ పరిధిలోకి రాదు.
  క్లెయిమ్ సమయంలో ఈ సర్టిఫికెట్‌తో పాటు లోపమున్న యూనిట్‌ను తప్పనిసరిగా చూపించాలి.
  సీరియల్ నంబర్ చెరిపివేయబడితే లేదా మార్చబడితే వారంటీ చెల్లదు.
  <b>KUMAR Pumps &amp; Motors</b> (శ్రీ లక్ష్మీ గణపతి ఇంజనీరింగ్ వర్క్స్ బ్రాండ్) తరఫున జారీ చేయబడింది.
</div>
</div>
"""
)

TEST_CERTIFICATE = (
	BRAND_CSS
	+ WRAP_OPEN
	+ HEADER
	+ """
<div class="k-title">{{ _("Pump Test Certificate") }}</div>

<table class="k-grid">
  <tr>
    <td class="k-label">{{ _("Certificate No") }}</td><td><b>{{ doc.name }}</b></td>
    <td class="k-label">{{ _("Test Date") }}</td><td>{{ frappe.utils.format_datetime(doc.test_date) }}</td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Serial No") }}</td><td><b>{{ doc.serial_no }}</b></td>
    <td class="k-label">{{ _("Model") }}</td><td>{{ doc.pump_model }}</td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Test Bench") }}</td><td>{{ doc.test_bench or "" }}</td>
    <td class="k-label">{{ _("Standard") }}</td><td>{{ doc.bis_standard_ref or "" }}</td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Supply") }}</td><td>{{ doc.supply_voltage_v }} V, {{ doc.frequency_hz }} Hz</td>
    <td class="k-label">{{ _("Tested By") }}</td><td>{{ doc.tested_by or "" }}</td>
  </tr>
</table>

<table class="k-grid">
  <tr>
    <td class="k-label" colspan="4" style="text-align:center;background:#0b5394;color:#fff">
      {{ _("Performance Duty Points") }}
    </td>
  </tr>
</table>
<table class="k-grid">
  <tr>
    <td class="k-label">{{ _("Head (m)") }}</td><td class="k-label">{{ _("Discharge (LPM)") }}</td>
    <td class="k-label">{{ _("Input Power (kW)") }}</td><td class="k-label">{{ _("Current (A)") }}</td>
    <td class="k-label">{{ _("Speed (RPM)") }}</td><td class="k-label">{{ _("Efficiency %") }}</td>
  </tr>
  {% for r in doc.duty_points %}
  <tr{% if r.is_duty_point %} style="background:#f2f6fb;font-weight:600"{% endif %}>
    <td>{{ r.head_m }}</td><td>{{ r.discharge_lpm }}</td><td>{{ r.input_power_kw }}</td>
    <td>{{ r.current_a }}</td><td>{{ r.speed_rpm }}</td><td>{{ r.efficiency_pct }}</td>
  </tr>
  {% endfor %}
</table>

<table class="k-grid">
  <tr>
    <td class="k-label">{{ _("No Load Current (A)") }}</td><td>{{ doc.no_load_current_a }} A</td>
    <td class="k-label">{{ _("Full Load Current (A)") }}</td><td>{{ doc.full_load_current_a }} A</td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Insulation Resistance (Mohm)") }}</td><td>{{ doc.insulation_resistance_mohm }} M&#8486;</td>
    <td class="k-label">{{ _("HiPot") }} ({{ doc.hipot_voltage_kv }} kV)</td>
    <td>{{ _(doc.hipot_result) if doc.hipot_result else "" }}</td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Hydrostatic") }}</td>
    <td>{{ doc.hydrostatic_test_pressure }} kg/cm&sup2; - {{ _(doc.hydrostatic_result) if doc.hydrostatic_result else "" }}</td>
    <td class="k-label">{{ _("Vibration / Noise") }}</td>
    <td>{{ doc.vibration_mm_s }} mm/s / {{ doc.noise_db }} dB</td>
  </tr>
</table>

<div style="text-align:center;margin:16px 0">
  <span class="k-badge {% if doc.overall_result == 'Pass' %}k-ok{% else %}k-no{% endif %}">
    {{ _("Result") }}: {{ _(doc.overall_result) }}
  </span>
</div>

<div class="k-sign">
  <div>{{ _("Tested By") }}</div><div>{{ _("Quality Engineer") }}</div>
  <div>{{ _("For KUMAR Pumps &amp; Motors") }}</div>
</div>
<div class="k-foot">
  {{ _("This unit has been tested in accordance with the referenced Bureau of Indian Standards specification before dispatch. Readings are recorded at the test bench under stated supply conditions.") }}
</div>
</div>
"""
)

JOB_CARD = (
	BRAND_CSS
	+ WRAP_OPEN
	+ HEADER
	+ """
<div class="k-title">{{ _("Service Job Card") }}</div>

<table class="k-grid">
  <tr>
    <td class="k-label">{{ _("Job Card") }}</td><td><b>{{ doc.name }}</b></td>
    <td class="k-label">{{ _("Visit Date") }}</td><td>{{ frappe.utils.format_date(doc.visit_date) }}</td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Service Request") }}</td><td>{{ doc.service_request }}</td>
    <td class="k-label">{{ _("Visit Type") }}</td><td>{{ _(doc.visit_type) if doc.visit_type else "" }}</td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Serial No") }}</td><td><b>{{ doc.serial_no }}</b></td>
    <td class="k-label">{{ _("Technician") }}</td><td>{{ doc.technician }}</td>
  </tr>
</table>

<table class="k-grid">
  <tr><td class="k-label">{{ _("Findings") }}</td><td colspan="3">{{ doc.findings or "" }}</td></tr>
  <tr><td class="k-label">{{ _("Action Taken") }}</td><td colspan="3">{{ doc.action_taken or "" }}</td></tr>
</table>

{% if doc.parts_used %}
<table class="k-grid">
  <tr>
    <td class="k-label">{{ _("Part") }}</td><td class="k-label">{{ _("Qty") }}</td>
    <td class="k-label">{{ _("Rate") }}</td><td class="k-label">{{ _("Amount") }}</td>
    <td class="k-label">{{ _("Warranty") }}</td>
  </tr>
  {% for r in doc.parts_used %}
  <tr>
    <td>{{ r.item_name or r.item_code }}</td><td>{{ r.qty }}</td>
    <td>{{ frappe.utils.fmt_money(r.rate, currency="INR") }}</td>
    <td>{{ frappe.utils.fmt_money(r.amount, currency="INR") }}</td>
    <td>{{ _("Yes") if r.is_warranty_replacement else _("No") }}</td>
  </tr>
  {% endfor %}
</table>
{% endif %}

<table class="k-grid">
  <tr>
    <td class="k-label">{{ _("Chargeable") }}</td>
    <td>{{ _("Yes") if doc.is_chargeable else _("No - under warranty") }}</td>
    <td class="k-label">{{ _("Labour Charge") }}</td>
    <td>{{ frappe.utils.fmt_money(doc.labour_charge, currency="INR") }}</td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Total Parts Value") }}</td>
    <td>{{ frappe.utils.fmt_money(doc.total_parts_value, currency="INR") }}</td>
    <td class="k-label">{{ _("Grand Total") }}</td>
    <td><b>{{ frappe.utils.fmt_money(doc.grand_total, currency="INR") }}</b></td>
  </tr>
</table>

<div class="k-sign">
  <div>{{ _("Customer Signature") }}</div><div>{{ _("Technician") }}</div>
  <div>{{ _("Service Centre") }}</div>
</div>
</div>
"""
)

ROUTE_CARD = (
	BRAND_CSS
	+ WRAP_OPEN
	+ HEADER
	+ """
<div class="k-title">{{ _("Route Card / Traveller") }}</div>

<table class="k-grid">
  <tr>
    <td class="k-label">{{ _("Work Order") }}</td><td><b>{{ doc.name }}</b></td>
    <td class="k-label">{{ _("Item") }}</td><td>{{ doc.production_item }}</td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Qty") }}</td><td>{{ doc.qty }}</td>
    <td class="k-label">{{ _("Planned Start") }}</td>
    <td>{{ frappe.utils.format_datetime(doc.planned_start_date) }}</td>
  </tr>
  <tr>
    <td class="k-label">{{ _("Heat No") }}</td><td>{{ doc.custom_heat_no or "________________" }}</td>
    <td class="k-label">{{ _("Winding Batch") }}</td>
    <td>{{ doc.custom_winding_batch or "________________" }}</td>
  </tr>
</table>

<table class="k-grid">
  <tr>
    <td class="k-label" style="width:6%">#</td>
    <td class="k-label" style="width:28%">{{ _("Operation") }}</td>
    <td class="k-label" style="width:20%">{{ _("Workstation") }}</td>
    <td class="k-label" style="width:14%">{{ _("Date") }}</td>
    <td class="k-label" style="width:16%">{{ _("Operator") }}</td>
    <td class="k-label" style="width:16%">{{ _("Sign / QC") }}</td>
  </tr>
  {% for op in doc.operations %}
  <tr>
    <td>{{ loop.index }}</td><td>{{ _(op.operation) }}</td><td>{{ op.workstation or "" }}</td>
    <td></td><td></td><td></td>
  </tr>
  {% endfor %}
  {% if not doc.operations %}
    {% for name in ["Moulding", "Melting & Pouring", "Fettling & Shot Blast", "Machining",
                    "Grinding", "Winding", "Varnishing & Curing", "Assembly",
                    "Performance Testing", "Painting & Packing"] %}
    <tr><td>{{ loop.index }}</td><td>{{ _(name) }}</td><td></td><td></td><td></td><td></td></tr>
    {% endfor %}
  {% endif %}
</table>

<div class="k-foot">
  {{ _("Record the heat number and winding batch on this card at the point of use, and enter them into the system at final assembly. Every finished pump must carry a serial number before it leaves the test bay.") }}
</div>
</div>
"""
)


def _make(name, doctype, html, *, page_size="A4"):
	doc = (
		frappe.get_doc("Print Format", name)
		if frappe.db.exists("Print Format", name)
		else frappe.new_doc("Print Format")
	)
	doc.update(
		{
			"name": name,
			"doc_type": doctype,
			"module": MODULE,
			"print_format_type": "Jinja",
			"standard": "No",
			"custom_format": 1,
			"disabled": 0,
			"html": html,
			"page_size": page_size,
			"margin_top": 10,
			"margin_bottom": 10,
			"margin_left": 10,
			"margin_right": 10,
		}
	)
	doc.flags.ignore_permissions = True
	if frappe.db.exists("Print Format", name):
		doc.save(ignore_permissions=True)
	else:
		doc.insert(ignore_permissions=True)


def build_all():
	_make("KUMAR Warranty Certificate", "Pump Registration", WARRANTY_CARD, page_size="A5")
	_make("KUMAR Pump Test Certificate", "Pump Test Certificate", TEST_CERTIFICATE)
	_make("KUMAR Service Job Card", "Service Visit", JOB_CARD, page_size="A5")
	_make("KUMAR Route Card", "Work Order", ROUTE_CARD)
	frappe.db.commit()
