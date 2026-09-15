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

# The payslip. Laid out with tables, not flexbox: wkhtmltopdf's WebKit predates
# flex, and this is the one page an employee will print or forward as a PDF.
# It carries its own KUMAR header, so the site letterhead is suppressed here -
# otherwise the PDF shows two company headers stacked on top of each other.
SALARY_SLIP = (
	"""
<style>
  .letter-head { display:none !important; }
  .ps { font-family: %s; color:#1f2933; font-size:11px; }
  .ps table { width:100%%; border-collapse:collapse; }
  .ps td, .ps th { vertical-align:top; }
  .ps-brand { font-size:30px; font-weight:800; color:#0b5394; letter-spacing:1.5px; line-height:1; }
  .ps-co { font-size:9.5px; color:#52606d; line-height:1.6; margin-top:5px; }
  .ps-doc { text-align:right; }
  .ps-doc-t { font-size:19px; font-weight:800; letter-spacing:4px; color:#0b5394; }
  .ps-month { display:inline-block; white-space:nowrap; margin-top:7px; background:#0b5394; color:#fff;
              padding:4px 14px; border-radius:12px; font-weight:700; font-size:11.5px; }
  .ps-draft { display:inline-block; margin-top:7px; margin-left:4px; background:#fce8e6; color:#a50e0e;
              border:1px solid #a50e0e; padding:3px 10px; border-radius:12px; font-weight:700; font-size:10px; }
  .ps-ref { font-size:9px; color:#7b8794; margin-top:6px; }
  .ps-rule { height:4px; background:#0b5394; margin-top:10px; }
  .ps-rule2 { height:2px; background:#f5a623; }

  .ps-card { border:1px solid #d9e2ec; border-radius:6px; margin-top:10px; }
  .ps-who td { padding:10px 14px 5px; vertical-align:middle; }
  .ps-photo { width:70px; }
  .ps-photo img { width:60px; height:60px; border-radius:8px; border:1px solid #d9e2ec; }
  .ps-name { font-size:17px; font-weight:800; color:#102a43; }
  .ps-role { color:#486581; font-size:11px; margin-top:2px; }
  .ps-id { text-align:right; font-size:10px; color:#7b8794; }
  .ps-id b { display:block; font-size:13px; color:#243b53; }
  .ps-kv td { padding:4px 14px; border-top:1px solid #f0f4f8; }
  .ps-kv td.k { color:#7b8794; font-size:9px; text-transform:uppercase; letter-spacing:.6px; width:16%%; padding-right:4px; }
  .ps-kv td.v { font-weight:600; color:#243b53; width:34%%; }

  .ps-stats { margin-top:10px; border:1px solid #d9e2ec; border-radius:6px; }
  .ps-stats td { text-align:center; padding:7px 4px; border-left:1px solid #d9e2ec; width:20%%; }
  .ps-stats td.first { border-left:none; }
  .ps-num { font-size:18px; font-weight:800; color:#0b5394; }
  .ps-num.warn { color:#b44d12; }
  .ps-lbl { font-size:8.5px; color:#7b8794; text-transform:uppercase; letter-spacing:.7px; margin-top:2px; }

  .ps-pay { margin-top:10px; }
  .ps-pay th { background:#0b5394; color:#fff; font-size:9.5px; text-transform:uppercase; letter-spacing:1px;
               padding:7px 10px; text-align:left; }
  .ps-pay th.r, .ps-pay td.r { text-align:right; }
  .ps-pay td { padding:5px 10px; border-bottom:1px solid #eef2f6; }
  .ps-pay td.gap, .ps-pay th.gap { width:3%%; background:#fff; border:none; padding:0; }
  .ps-pay tr.tot td { background:#eef4fb; font-weight:800; color:#102a43; border-top:2px solid #0b5394; border-bottom:none; }
  .ps-pay tr.tot td.gap { background:#fff; border-top:none; }

  .ps-net { margin-top:10px; background:#0b5394; color:#fff; border-radius:6px; }
  .ps-net td { padding:10px 18px; vertical-align:middle; }
  .ps-net-lbl { font-size:9.5px; letter-spacing:2px; text-transform:uppercase; color:#c9dcf0; }
  .ps-net-amt { font-size:28px; font-weight:800; line-height:1.15; }
  .ps-net-words { font-size:10.5px; color:#e3eefa; margin-top:3px; }
  .ps-net-bank { text-align:right; font-size:10px; color:#c9dcf0; line-height:1.6; }
  .ps-net-bank b { color:#fff; font-size:11.5px; }

  .ps-sub { margin-top:12px; font-size:9.5px; font-weight:800; color:#0b5394; text-transform:uppercase; letter-spacing:1.2px; }
  .ps-leave { margin-top:5px; }
  .ps-leave th { font-size:9px; color:#52606d; text-transform:uppercase; letter-spacing:.6px; text-align:right;
                 padding:5px 10px; border-bottom:1px solid #bcccdc; background:#f5f7fa; }
  .ps-leave th.l, .ps-leave td.l { text-align:left; }
  .ps-leave td { text-align:right; padding:4px 10px; border-bottom:1px solid #eef2f6; }

  .ps-foot { margin-top:14px; border-top:1px dashed #bcccdc; padding-top:9px; font-size:9px; color:#7b8794;
             text-align:center; line-height:1.7; }
</style>
"""
	% FONT_STACK
	+ WRAP_OPEN.replace("k-wrap", "ps k-wrap")
	+ """
{%- set emp = frappe.db.get_value("Employee", doc.employee,
      ["pan_number", "provident_fund_account", "date_of_joining", "grade", "image"], as_dict=True) or {} -%}
{%- set earnings = doc.earnings | rejectattr("statistical_component") | list -%}
{%- set deductions = doc.deductions | rejectattr("statistical_component") | list -%}
{%- set rows = [earnings | length, deductions | length] | max -%}
{%- set lop = (doc.total_working_days or 0) - (doc.payment_days or 0) -%}
{%- macro days(v) -%}{{ "%g" | format(v or 0) }}{%- endmacro -%}

<table>
  <tr>
    <td>
      <div class="ps-brand">KUMAR</div>
      <div class="ps-co">
        <b>{{ _("Sri Lakshmi Ganapathi Engineering Works") }}</b> &middot; {{ _("Pumps &amp; Motors") }} &middot; ISO 9001:2015<br>
        {{ _("Plot 9-14 &amp; 17-24, Industrial Estate, Sultanabad,") }}
        {{ _("Tenali - 522202, Guntur Dist., Andhra Pradesh") }}
      </div>
    </td>
    <td class="ps-doc" style="width:38%">
      <div class="ps-doc-t">{{ _("PAYSLIP") }}</div>
      <span class="ps-month">{{ frappe.utils.formatdate(doc.start_date, "MMMM yyyy") }}</span>
      {%- if doc.docstatus == 0 %}<span class="ps-draft">{{ _("DRAFT") }}</span>{% endif %}
      {%- if doc.docstatus == 2 %}<span class="ps-draft">{{ _("CANCELLED") }}</span>{% endif %}
      <div class="ps-ref">{{ doc.name }}</div>
    </td>
  </tr>
</table>
<div class="ps-rule"></div><div class="ps-rule2"></div>

<div class="ps-card">
  <table class="ps-who">
    <tr>
      {%- if emp.image %}
      <td class="ps-photo"><img src="{{ emp.image }}"></td>
      {%- endif %}
      <td>
        <div class="ps-name">{{ doc.employee_name }}</div>
        <div class="ps-role">{{ _(doc.designation) if doc.designation else "" }}{% if doc.department %} &middot; {{ doc.department.rsplit(" - ", 1)[0] }}{% endif %}</div>
      </td>
      <td class="ps-id">{{ _("Employee ID") }}<b>{{ doc.employee }}</b></td>
    </tr>
  </table>
  <table class="ps-kv">
    <tr>
      <td class="k">{{ _("Pay Period") }}</td>
      <td class="v">{{ frappe.utils.format_date(doc.start_date) }} &ndash; {{ frappe.utils.format_date(doc.end_date) }}</td>
      <td class="k">{{ _("Date of Joining") }}</td>
      <td class="v">{{ frappe.utils.format_date(emp.date_of_joining) if emp.date_of_joining else "-" }}</td>
    </tr>
    <tr>
      <td class="k">{{ _("Location") }}</td><td class="v">{{ doc.branch or "-" }}</td>
      <td class="k">{{ _("Grade") }}</td><td class="v">{{ emp.grade or "-" }}</td>
    </tr>
    <tr>
      <td class="k">{{ _("PAN") }}</td><td class="v">{{ emp.pan_number or "-" }}</td>
      <td class="k">{{ _("PF Account") }}</td><td class="v">{{ emp.provident_fund_account or "-" }}</td>
    </tr>
    <tr>
      <td class="k">{{ _("Bank") }}</td><td class="v">{{ doc.bank_name or "-" }}</td>
      <td class="k">{{ _("Account No") }}</td>
      <td class="v">{% if doc.bank_account_no %}XXXXXX{{ doc.bank_account_no[-4:] }}{% else %}-{% endif %}</td>
    </tr>
  </table>
</div>

<table class="ps-stats">
  <tr>
    <td class="first"><div class="ps-num">{{ days(doc.total_working_days) }}</div><div class="ps-lbl">{{ _("Working Days") }}</div></td>
    <td><div class="ps-num">{{ days(doc.payment_days) }}</div><div class="ps-lbl">{{ _("Days Paid") }}</div></td>
    <td><div class="ps-num{% if lop > 0 %} warn{% endif %}">{{ days(lop) }}</div><div class="ps-lbl">{{ _("Loss of Pay") }}</div></td>
    <td><div class="ps-num">{{ doc.get_formatted("gross_pay") }}</div><div class="ps-lbl">{{ _("Gross Earnings") }}</div></td>
    <td><div class="ps-num">{{ doc.get_formatted("total_deduction") }}</div><div class="ps-lbl">{{ _("Deductions") }}</div></td>
  </tr>
</table>

<table class="ps-pay">
  <tr>
    <th>{{ _("Earnings") }}</th><th class="r">{{ _("Amount") }}</th>
    <th class="gap"></th>
    <th>{{ _("Deductions") }}</th><th class="r">{{ _("Amount") }}</th>
  </tr>
  {%- for i in range(rows) %}
  <tr>
    {%- if i < earnings | length %}
    <td>{{ _(earnings[i].salary_component) }}</td><td class="r">{{ earnings[i].get_formatted("amount", doc) }}</td>
    {%- else %}<td></td><td></td>{% endif %}
    <td class="gap"></td>
    {%- if i < deductions | length %}
    <td>{{ _(deductions[i].salary_component) }}</td><td class="r">{{ deductions[i].get_formatted("amount", doc) }}</td>
    {%- else %}<td></td><td></td>{% endif %}
  </tr>
  {%- endfor %}
  <tr class="tot">
    <td>{{ _("Gross Earnings") }}</td><td class="r">{{ doc.get_formatted("gross_pay") }}</td>
    <td class="gap"></td>
    <td>{{ _("Total Deductions") }}</td><td class="r">{{ doc.get_formatted("total_deduction") }}</td>
  </tr>
</table>

<table class="ps-net">
  <tr>
    <td>
      <div class="ps-net-lbl">{{ _("Net Pay") }}</div>
      <div class="ps-net-amt">{{ doc.get_formatted("rounded_total" if doc.rounded_total else "net_pay") }}</div>
      <div class="ps-net-words">{{ doc.total_in_words or "" }}</div>
    </td>
    <td class="ps-net-bank" style="width:36%">
      {%- if doc.bank_account_no %}
      {{ _("Credited by bank transfer to") }}<br>
      <b>{{ doc.bank_name or "" }} &middot; XXXXXX{{ doc.bank_account_no[-4:] }}</b><br>
      {%- endif %}
      {{ _("Pay date") }}: <b>{{ frappe.utils.format_date(doc.posting_date) }}</b>
    </td>
  </tr>
</table>

{%- if doc.leave_details %}
<div class="ps-sub">{{ _("Leave Balance") }}</div>
<table class="ps-leave">
  <tr>
    <th class="l">{{ _("Leave Type") }}</th><th>{{ _("Allocated") }}</th><th>{{ _("Taken") }}</th>
    <th>{{ _("Pending Approval") }}</th><th>{{ _("Available") }}</th>
  </tr>
  {%- for l in doc.leave_details %}
  <tr>
    <td class="l">{{ _(l.leave_type) }}</td><td>{{ days(l.total_allocated_leaves) }}</td><td>{{ days(l.used_leaves) }}</td>
    <td>{{ days(l.pending_leaves) }}</td><td><b>{{ days(l.available_leaves) }}</b></td>
  </tr>
  {%- endfor %}
</table>
{%- endif %}

<div class="ps-foot">
  {{ _("This is a computer-generated payslip and does not require a signature.") }}<br>
  {{ _("For any query about this payslip, write to HR at the Tenali plant.") }}
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
	_make("KUMAR Salary Slip", "Salary Slip", SALARY_SLIP)

	# the payslip opens in KUMAR's own format, not HRMS's stock one
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	make_property_setter(
		"Salary Slip", None, "default_print_format", "KUMAR Salary Slip", "Data", for_doctype=True
	)
	frappe.db.commit()
	frappe.clear_cache(doctype="Salary Slip")
