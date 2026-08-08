"""Every DocType the app owns, defined in code.

With developer_mode on, creating these through the ORM makes Frappe export the
JSON into the app folder, so the app ships real standard DocTypes while the
definitions stay readable and diffable in one place.
"""

import frappe

from kumar_service.setup.common import column, f, make_doctype, perm, section
from kumar_service.utils import CH_DEALER, CH_DIRECT

CATEGORY_ICONS = "Piston Pumps\nElectrical Motors\nSubmersible Pumps\nCentrifugal Monobloc"

COMPLAINT_CATEGORIES = "\n".join(
	[
		"No Discharge",
		"Low Discharge",
		"Motor Burnt",
		"Noise & Vibration",
		"Leakage",
		"Tripping",
		"Seal Failure",
		"Bearing Failure",
		"Impeller Damage",
		"Cable Fault",
		"Installation Issue",
		"Other",
	]
)

ROOT_CAUSES = "\n".join(
	[
		"",
		"Manufacturing Defect",
		"Installation Error",
		"Voltage Fluctuation",
		"Dry Run",
		"Water Quality",
		"Wear & Tear",
		"Misuse",
		"Not a Defect",
	]
)

# OW = openwell submersible. The brochure keeps it apart from the V-series
# borewell families because it runs an aluminium rotor, not copper.
FAMILY_CODES = "PP\nPPS\nPPS3PLG\nJM\nSMB\nHMB\nBP\nV3\nV4\nV6\nV8\nOW\nHAND\nMOTOR\nENGINE"

# the channel strings live in utils so the runtime controller and the portal
# can compare against them without importing this dev-time module
# Leading blank on purpose. Frappe fills an empty Select with its FIRST option
# before validate() runs, so without the blank the channel would always arrive
# pre-set and could never be derived from the outlet.
SALE_CHANNELS = f"\n{CH_DEALER}\n{CH_DIRECT}"
# double quotes, deliberately: CH_DEALER contains an apostrophe ("Dealer's Own
# Invoice") and wrapping it in single quotes ends the JS string early, leaving
# a depends_on that throws and a field that never shows.
DEP_DEALER = f'eval:doc.sale_channel=="{CH_DEALER}"'


def build_all():
	pump_category()
	pump_model_spec_point()
	pump_model()
	dealer()
	service_technician()
	settings()
	pump_registration()
	service_part_used()
	service_request()
	service_visit()
	claim_part_row()
	warranty_claim()
	heat_spectro_reading()
	heat_record()
	winding_batch_record()
	test_duty_point()
	pump_test_certificate()
	# second pass: now that every DocType exists, close the circular links
	service_request()
	frappe.db.commit()


# --------------------------------------------------------------- masters


def pump_category():
	make_doctype(
		"Pump Category",
		[
			f("category_name", "Category Name", reqd=1, unique=1, in_list_view=1),
			f("abbr", "Abbreviation", length=5, in_list_view=1),
			f("default_warranty_months", "Default Warranty (Months)", "Int", default="12", in_list_view=1),
			column("cb1"),
			f("icon", "Icon"),
			f("image", "Image", "Attach Image"),
			f("is_active", "Is Active", "Check", default="1"),
			section("sb1"),
			f("description", "Description", "Small Text"),
		],
		autoname="field:category_name",
		naming_rule="By fieldname",
		description="Product family, e.g. Submersible Pumps. Drives the default warranty period.",
		permissions=[
			perm("System Manager", delete=1),
			perm("Production Manager"),
			perm("Quality Engineer", create=0, write=1),
			perm("Service Manager", create=0, write=0),
			perm("Dealer", create=0, write=0, export=0),
		],
	)


def pump_model_spec_point():
	make_doctype(
		"Pump Model Spec Point",
		[
			f("head_m", "Head (m)", "Float", in_list_view=1),
			f("discharge", "Discharge", "Float", in_list_view=1),
			f("efficiency_pct", "Efficiency %", "Float", in_list_view=1),
			f("input_kw", "Input kW", "Float", in_list_view=1),
			f("current_amp", "Current (A)", "Float", in_list_view=1),
		],
		istable=1,
	)


def pump_model():
	make_doctype(
		"Pump Model",
		[
			f("model_code", "Model Code", reqd=1, unique=1, in_list_view=1, bold=1),
			f("pump_category", "Pump Category", "Link", options="Pump Category", reqd=1, in_list_view=1),
			f("family_code", "Family Code", "Select", options=FAMILY_CODES, in_standard_filter=1),
			f("item", "Stock Item", "Link", options="Item"),
			column("cb1"),
			f("hp", "HP", "Float", reqd=1, in_list_view=1),
			f("kw", "kW", "Float", read_only=1, description="Auto = HP x 0.7457"),
			f("phase", "Phase", "Select", options="\nSingle Phase\nThree Phase", in_standard_filter=1),
			f("voltage_range", "Voltage Range"),
			f("rpm", "RPM", "Int"),
			section("sb_mech", "Mechanical"),
			f("suction_size_inch", "Suction Size (inch)"),
			f("delivery_size_inch", "Delivery Size (inch)"),
			f("impeller_material", "Impeller Material", "Select",
				options="\nGunmetal\nCast Iron\nStainless Steel\nThermoplastic"),
			column("cb2"),
			f("rotor_type", "Rotor Type", "Select", options="\nCopper\nAluminium Die Cast"),
			f("base_type", "Base Type", "Select", options="\nSquare\nRound\nNA"),
			f("stage_type", "Stage Type", "Select", options="\nSingle Stage\nDouble Stage\nNA"),
			section("sb_perf", "Performance"),
			f("head_min_m", "Head Min (m)", "Float"),
			f("head_max_m", "Head Max (m)", "Float"),
			column("cb3"),
			f("discharge_min", "Discharge Min", "Float"),
			f("discharge_max", "Discharge Max", "Float"),
			f("discharge_uom", "Discharge UOM", "Select", options="LPM\nLPH\nLPS"),
			section("sb_curve"),
			f("performance_curve", "Performance Curve", "Table", options="Pump Model Spec Point"),
			section("sb_meta", "Compliance"),
			f("bis_standard", "BIS Standard", description="e.g. IS 8034, IS 9079, IS 7538"),
			f("warranty_months", "Warranty (Months)", "Int",
				description="Leave 0 to inherit the category default"),
			column("cb4"),
			f("is_active", "Is Active", "Check", default="1"),
		],
		autoname="field:model_code",
		naming_rule="By fieldname",
		title_field="model_code",
		search_fields="pump_category,hp,phase",
		description="One catalogue model, e.g. KSMB50P3(4x3). Specs here drive warranty and test limits.",
		permissions=[
			perm("System Manager", delete=1),
			perm("Production Manager"),
			perm("Quality Engineer"),
			perm("Service Manager", create=0, write=0),
			perm("Service Technician", create=0, write=0),
			perm("Dealer", create=0, write=0, export=0),
		],
	)


def dealer():
	make_doctype(
		"Dealer",
		[
			f("dealer_name", "Dealer Name", reqd=1, in_list_view=1, bold=1),
			f("dealer_code", "Dealer Code", unique=1, in_list_view=1),
			f("dealer_type", "Dealer Type", "Select",
				options="Branch Office\nAuthorised Distributor\nDealer\nSub-Dealer\nService Centre",
				default="Dealer", in_list_view=1, in_standard_filter=1),
			# dealer_type says where an outlet sits in the network; this says who
			# owns it. They are different questions and the answer to the second
			# decides whose invoice the end customer walks away with.
			f("is_own_outlet", "Is KUMAR's Own Outlet", "Check", in_standard_filter=1,
				description="Tick for a branch or showroom KUMAR owns: its sale to the end "
				"customer is a KUMAR invoice in our own books. Leave clear for an "
				"independent firm - it buys from us on our invoice, then raises its own "
				"invoice to the customer, which never enters our books."),
			column("cb1"),
			f("parent_dealer", "Parent Dealer", "Link", options="Dealer",
				ignore_user_permissions=1),
			f("is_group", "Is Group", "Check"),
			f("status", "Status", "Select", options="Active\nSuspended\nTerminated",
				default="Active", in_standard_filter=1),
			f("onboarding_date", "Onboarding Date", "Date"),
			section("sb_contact", "Contact"),
			f("contact_person", "Contact Person"),
			f("mobile_no", "Mobile No"),
			f("landline", "Landline"),
			f("email_id", "Email", "Data", options="Email"),
			column("cb2"),
			f("address_line", "Address", "Small Text"),
			f("city", "City"),
			f("state", "State"),
			f("pincode", "Pincode"),
			section("sb_link", "Links"),
			f("customer", "Customer", "Link", options="Customer"),
			f("territory", "Territory", "Link", options="Territory"),
			f("portal_user", "Portal User", "Link", options="User",
				description="The login this dealer uses. Row-level access is derived from this."),
			column("cb3"),
			f("gstin", "GSTIN"),
			f("credit_limit", "Credit Limit", "Currency"),
			f("service_centre_flag", "Is Service Centre", "Check"),
			section("sb_tree"),
			f("lft", "lft", "Int", hidden=1, read_only=1, no_copy=1, print_hide=1),
			f("rgt", "rgt", "Int", hidden=1, read_only=1, no_copy=1, print_hide=1),
			f("old_parent", "old_parent", "Link", options="Dealer", hidden=1, read_only=1,
				no_copy=1, print_hide=1),
		],
		autoname="field:dealer_name",
		naming_rule="By fieldname",
		is_tree=1,
		title_field="dealer_name",
		search_fields="dealer_code,city,state",
		description="Sales/service network. Self-referencing tree: Branch -> Distributor -> Dealer -> Sub-Dealer.",
		permissions=[
			perm("System Manager", delete=1),
			perm("Dealer Manager", delete=1),
			perm("Service Manager"),
			perm("Dealer", create=0, write=0, export=0),
			perm("Service Technician", create=0, write=0),
		],
	)


def service_technician():
	make_doctype(
		"Service Technician",
		[
			f("technician_name", "Technician Name", reqd=1, in_list_view=1, bold=1),
			f("employee", "Employee", "Link", options="Employee"),
			f("user", "User", "Link", options="User"),
			column("cb1"),
			f("dealer", "Service Centre / Dealer", "Link", options="Dealer", in_list_view=1),
			f("mobile_no", "Mobile No", in_list_view=1),
			f("territory", "Territory", "Link", options="Territory"),
			f("is_active", "Is Active", "Check", default="1", in_standard_filter=1),
		],
		autoname="field:technician_name",
		naming_rule="By fieldname",
		description="Field engineer who attends service requests.",
		permissions=[
			perm("System Manager", delete=1),
			perm("Service Manager", delete=1),
			perm("Service Technician", create=0, write=0),
			perm("Dealer", create=0, write=0, export=0),
		],
	)


def settings():
	make_doctype(
		"Kumar Service Settings",
		[
			section("sb_warranty", "Warranty"),
			f("default_warranty_months", "Default Warranty (Months)", "Int", default="12"),
			f("warranty_from", "Warranty Starts From", "Select",
				options="Sale Date\nManufacturing Date", default="Sale Date"),
			f("allow_dealer_backdated_registration_days", "Allow Dealer Backdated Registration (Days)",
				"Int", default="30"),
			column("cb1"),
			f("warranty_reminder_days", "Warranty Reminder Days", "Data", default="30,7",
				description="Comma separated days before expiry to remind"),
			f("certificate_issuer", "Certificate Issued On Behalf Of", "Data",
				default="KUMAR Pumps & Motors"),
			section("sb_sla", "Service SLA"),
			f("sla_response_hours", "Response Hours", "Int", default="24"),
			f("sla_resolution_hours", "Resolution Hours", "Int", default="72"),
			column("cb2"),
			f("repeat_failure_window_days", "Repeat Failure Window (Days)", "Int", default="90"),
			f("default_service_centre", "Default Service Centre", "Link", options="Dealer"),
			section("sb_trace", "Traceability"),
			f("enable_heat_traceability", "Enable Heat Traceability", "Check", default="1"),
			f("enable_test_certificate", "Enable Test Certificate", "Check", default="1"),
			column("cb3"),
			f("enforce_qc_before_dispatch", "Block Dispatch Unless QC Passed", "Check", default="1"),
			f("batch_failure_threshold_pct", "Batch Failure Alert Threshold %", "Float", default="5"),
			section("sb_qr", "Identity & QR"),
			f("serial_format_template", "Serial Format (regex)", "Data",
				default="^KP-[A-Z0-9()x.]+-\\d{4}-\\d{5}$"),
			f("qr_base_url", "QR Base URL", "Data",
				default="https://kumarpumps.co.in/warranty-check"),
			column("cb4"),
			f("sms_gateway_enabled", "SMS Enabled", "Check"),
			f("whatsapp_notification_enabled", "WhatsApp Enabled", "Check"),
		],
		issingle=1,
		description="Every configurable assumption lives here - nothing is hardcoded.",
		permissions=[perm("System Manager", delete=1), perm("Production Manager", create=0)],
	)


# ----------------------------------------------------- registration & service


def pump_registration():
	make_doctype(
		"Pump Registration",
		[
			f("naming_series", "Series", "Select", options="PREG-.YY.-.#####", default="PREG-.YY.-.#####",
				reqd=1, print_hide=1),
			f("serial_no", "Serial No", "Link", options="Serial No", reqd=1, in_list_view=1, bold=1),
			f("pump_model", "Pump Model", "Link", options="Pump Model", read_only=1, in_list_view=1),
			f("item_code", "Item", "Link", options="Item", read_only=1),
			column("cb1"),
			f("hp", "HP", "Float", read_only=1),
			f("phase", "Phase", "Data", read_only=1),
			f("manufacturing_date", "Manufacturing Date", "Date", read_only=1),
			section("sb_sale", "Sale to End Customer"),
			f("dealer", "Sold By", "Link", options="Dealer", reqd=1, in_list_view=1,
				in_standard_filter=1),
			# Two different businesses can hand a pump to the same farmer, and the
			# paperwork behind each is nothing alike. Everything else in this
			# section keys off this one field.
			# No default on purpose. A default is filled in before validate()
			# runs, so the channel would never actually be derived from the
			# outlet - a KUMAR branch selling over its own counter would be
			# filed as a dealer sale and then asked for a dealer invoice that
			# does not exist. Left blank, validate() derives it; anything the
			# user types is still honoured.
			f("sale_channel", "Sale Channel", "Select",
				options=SALE_CHANNELS, reqd=1, in_standard_filter=1,
				description="Set automatically from the outlet. Change it only if the "
				"paperwork really went the other way."),
			f("sale_date", "Sale Date", "Date", reqd=1, in_list_view=1,
				description="The day the END CUSTOMER got the pump - this starts the warranty."),
			column("cb2"),
			f("invoice_no", "Dealer's Invoice No", depends_on=DEP_DEALER,
				description="The dealer's own invoice to the customer, on the dealer's "
				"letterhead and GSTIN. We never raise this - we only record it, because "
				"it is the customer's proof of purchase when a claim comes in."),
			f("dealer_invoice_date", "Dealer's Invoice Date", "Date", depends_on=DEP_DEALER),
			f("dealer_gstin", "Dealer's GSTIN", read_only=1, depends_on=DEP_DEALER,
				fetch_from="dealer.gstin"),
			f("sales_invoice", "KUMAR Invoice", "Link", options="Sales Invoice",
				description="Our invoice. On a direct sale this IS the customer's invoice; "
				"through a dealer it is the invoice that sold the pump TO the dealer, kept "
				"for traceability only."),
			section("sb_src"),
			f("registration_source", "Source", "Select",
				options="Dealer Portal\nDesk\nMobile\nBulk Import\nAuto from Invoice", default="Desk"),
			column("cb2b"),
			f("registered_by", "Registered By", "Link", options="User", read_only=1),
			section("sb_cust", "End Customer"),
			f("end_customer_name", "Customer Name", reqd=1, in_list_view=1),
			f("end_customer_mobile", "Mobile", reqd=1, description="10 digits starting 6-9"),
			f("end_customer_email", "Email", "Data", options="Email"),
			column("cb3"),
			f("application_type", "Application", "Select",
				options="Domestic\nAgriculture\nIndustrial\nCommercial", default="Agriculture"),
			f("borewell_depth_ft", "Borewell Depth (ft)", "Float"),
			f("static_water_level_ft", "Static Water Level (ft)", "Float"),
			section("sb_addr", "Installation"),
			f("installation_address", "Address", "Small Text"),
			f("district", "District"),
			column("cb4"),
			f("state", "State"),
			f("pincode", "Pincode"),
			section("sb_warr", "Warranty"),
			f("warranty_months", "Warranty (Months)", "Int", read_only=1),
			f("warranty_start_date", "Warranty Start", "Date", read_only=1),
			column("cb5"),
			f("warranty_expiry_date", "Warranty Expiry", "Date", read_only=1, in_list_view=1),
			f("warranty_card_no", "Warranty Card No", read_only=1),
			section("sb_qr"),
			f("qr_url", "QR URL", "Data", read_only=1),
			f("qr_code", "QR Code", "Long Text", read_only=1, hidden=1, print_hide=1),
			f("amended_from", "Amended From", "Link", options="Pump Registration", read_only=1,
				no_copy=1, print_hide=1),
		],
		autoname="naming_series:",
		naming_rule="By \"Naming Series\" field",
		is_submittable=1,
		title_field="serial_no",
		search_fields="end_customer_name,end_customer_mobile,dealer",
		description="Dealer records a sale. This is what starts the warranty clock and issues the certificate.",
		permissions=[
			perm("System Manager", delete=1, submit=1, cancel=1, amend=1),
			perm("Dealer Manager", delete=1, submit=1, cancel=1, amend=1),
			perm("Service Manager", submit=1, cancel=1, amend=1),
			perm("Dealer", submit=1, amend=1, delete=0, export=0),
			perm("Service Technician", create=0, write=0),
			perm("Quality Engineer", create=0, write=0),
			perm("Warranty Approver", create=0, write=0),
		],
	)


def service_part_used():
	make_doctype(
		"Service Part Used",
		[
			f("item_code", "Item", "Link", options="Item", in_list_view=1, reqd=1),
			f("item_name", "Item Name", "Data", read_only=1, in_list_view=1),
			f("qty", "Qty", "Float", default="1", in_list_view=1),
			f("uom", "UOM", "Link", options="UOM"),
			f("rate", "Rate", "Currency", in_list_view=1),
			f("amount", "Amount", "Currency", read_only=1, in_list_view=1),
			f("is_warranty_replacement", "Warranty Replacement", "Check"),
			f("defective_part_returned", "Defective Part Returned", "Check"),
		],
		istable=1,
	)


def service_request():
	# Service Request and Kumar Warranty Claim point at each other. On the very
	# first build the claim DocType does not exist yet, so the link field is left
	# out and added by the second pass in build_all().
	claim_link = (
		[f("linked_claim", "Warranty Claim", "Link", options="Kumar Warranty Claim", read_only=1)]
		if frappe.db.exists("DocType", "Kumar Warranty Claim")
		else []
	)

	make_doctype(
		"Service Request",
		[
			f("naming_series", "Series", "Select", options="SR-.YY.-.#####", default="SR-.YY.-.#####",
				reqd=1, print_hide=1),
			f("serial_no", "Serial No", "Link", options="Serial No", reqd=1, in_list_view=1, bold=1),
			f("warranty_status_html", "Warranty", "HTML"),
			section("sb_snap", "Pump Snapshot"),
			f("pump_model", "Pump Model", "Link", options="Pump Model", read_only=1, in_list_view=1),
			f("hp", "HP", "Float", read_only=1),
			f("phase", "Phase", "Data", read_only=1),
			f("manufacturing_date", "Manufacturing Date", "Date", read_only=1),
			column("cb1"),
			f("dealer", "Dealer", "Link", options="Dealer", read_only=1, in_standard_filter=1),
			f("sale_date", "Sale Date", "Date", read_only=1),
			f("warranty_expiry_date", "Warranty Expiry", "Date", read_only=1),
			f("is_under_warranty", "Under Warranty", "Check", read_only=1, in_list_view=1),
			column("cb1b"),
			f("end_customer_name", "Customer", "Data", read_only=1),
			f("end_customer_mobile", "Mobile", "Data", read_only=1),
			f("is_repeat_failure", "Repeat Failure", "Check", read_only=1),
			section("sb_complaint", "Complaint"),
			f("complaint_category", "Category", "Select", options=COMPLAINT_CATEGORIES, reqd=1,
				in_list_view=1, in_standard_filter=1),
			f("priority", "Priority", "Select", options="Low\nMedium\nHigh\nCritical", default="Medium",
				in_standard_filter=1),
			f("reported_on", "Reported On", "Datetime", reqd=1, default="now"),
			column("cb2"),
			f("status", "Status", "Select",
				options="Open\nAssigned\nIn Progress\nAwaiting Parts\nResolved\nClosed\nCancelled",
				default="Open", in_list_view=1, in_standard_filter=1),
			f("assigned_technician", "Technician", "Link", options="Service Technician"),
			f("service_centre", "Service Centre", "Link", options="Dealer"),
			section("sb_desc"),
			f("complaint_description", "Complaint Description", "Text", reqd=1),
			section("sb_sla", "SLA"),
			f("response_due_on", "Response Due", "Datetime", read_only=1),
			f("first_response_on", "First Response", "Datetime"),
			column("cb3"),
			f("resolution_due_on", "Resolution Due", "Datetime", read_only=1),
			f("resolved_on", "Resolved On", "Datetime"),
			column("cb3b"),
			f("sla_status", "SLA Status", "Select", options="Ongoing\nResponded\nFulfilled\nFailed",
				default="Ongoing", read_only=1, in_standard_filter=1),
			section("sb_res", "Resolution"),
			f("resolution_summary", "Resolution Summary", "Text"),
			f("root_cause", "Root Cause", "Select", options=ROOT_CAUSES, in_standard_filter=1),
			*claim_link,
			section("sb_hist"),
			f("service_history_html", "Service History", "HTML"),
			f("amended_from", "Amended From", "Link", options="Service Request", read_only=1,
				no_copy=1, print_hide=1),
		],
		autoname="naming_series:",
		naming_rule="By \"Naming Series\" field",
		is_submittable=1,
		title_field="serial_no",
		search_fields="end_customer_name,end_customer_mobile,complaint_category",
		description="A complaint against one physical pump. Enter the serial and everything else fills itself.",
		permissions=[
			perm("System Manager", delete=1, submit=1, cancel=1, amend=1),
			perm("Service Manager", delete=1, submit=1, cancel=1, amend=1),
			perm("Service Technician", create=1, write=1, submit=1),
			perm("Dealer", create=1, write=1, submit=1, export=0),
			perm("Quality Engineer", create=0, write=0),
			perm("Warranty Approver", create=0, write=0),
		],
	)


def service_visit():
	make_doctype(
		"Service Visit",
		[
			f("naming_series", "Series", "Select", options="SV-.YY.-.#####", default="SV-.YY.-.#####",
				reqd=1, print_hide=1),
			f("service_request", "Service Request", "Link", options="Service Request", reqd=1,
				in_list_view=1),
			f("serial_no", "Serial No", "Link", options="Serial No", read_only=1, in_list_view=1),
			f("technician", "Technician", "Link", options="Service Technician", reqd=1, in_list_view=1),
			column("cb1"),
			f("visit_date", "Visit Date", "Date", reqd=1, default="Today", in_list_view=1),
			f("visit_type", "Visit Type", "Select", options="On-Site\nWorkshop\nTelephonic",
				default="On-Site", in_standard_filter=1),
			f("is_chargeable", "Chargeable", "Check",
				description="Set automatically from warranty status; override if needed"),
			section("sb_work", "Work Done"),
			f("findings", "Findings", "Text"),
			f("action_taken", "Action Taken", "Text"),
			section("sb_parts", "Parts"),
			f("parts_used", "Parts Used", "Table", options="Service Part Used"),
			f("total_parts_value", "Total Parts Value", "Currency", read_only=1),
			column("cb2"),
			f("labour_charge", "Labour Charge", "Currency"),
			f("grand_total", "Grand Total", "Currency", read_only=1, in_list_view=1),
			section("sb_cust", "Customer Sign-off"),
			f("customer_feedback", "Feedback", "Small Text"),
			f("customer_rating", "Rating", "Rating"),
			column("cb3"),
			f("customer_signature", "Signature", "Signature"),
			f("photo_1", "Photo 1", "Attach Image"),
			f("photo_2", "Photo 2", "Attach Image"),
			f("amended_from", "Amended From", "Link", options="Service Visit", read_only=1,
				no_copy=1, print_hide=1),
		],
		autoname="naming_series:",
		naming_rule="By \"Naming Series\" field",
		is_submittable=1,
		description="What the technician actually did, what parts went in, and what it cost.",
		permissions=[
			perm("System Manager", delete=1, submit=1, cancel=1, amend=1),
			perm("Service Manager", delete=1, submit=1, cancel=1, amend=1),
			perm("Service Technician", create=1, write=1, submit=1, amend=1),
			perm("Dealer", create=0, write=0, export=0),
			perm("Warranty Approver", create=0, write=0),
		],
	)


def claim_part_row():
	make_doctype(
		"Claim Part Row",
		[
			f("item_code", "Item", "Link", options="Item", in_list_view=1, reqd=1),
			f("item_name", "Item Name", read_only=1, in_list_view=1),
			f("qty", "Qty", "Float", default="1", in_list_view=1),
			f("rate", "Rate", "Currency", in_list_view=1),
			f("amount", "Amount", "Currency", read_only=1, in_list_view=1),
			f("defect_observed", "Defect Observed", "Small Text"),
		],
		istable=1,
	)


def warranty_claim():
	make_doctype(
		"Kumar Warranty Claim",
		[
			f("naming_series", "Series", "Select", options="WC-.YY.-.#####", default="WC-.YY.-.#####",
				reqd=1, print_hide=1),
			f("service_request", "Service Request", "Link", options="Service Request", in_list_view=1),
			f("serial_no", "Serial No", "Link", options="Serial No", reqd=1, in_list_view=1),
			f("dealer", "Dealer", "Link", options="Dealer", reqd=1, in_standard_filter=1),
			column("cb1"),
			f("claim_date", "Claim Date", "Date", reqd=1, default="Today", in_list_view=1),
			f("claim_type", "Claim Type", "Select",
				options="Part Replacement\nFull Unit Replacement\nRepair Reimbursement",
				default="Part Replacement", in_standard_filter=1),
			# allow_on_submit is what makes the workflow usable at all. Every
			# state past Draft is docstatus 1, so without it the first
			# transition submits the claim and then nothing can move it again -
			# "Not allowed to change Status after submission". The approved
			# amount and credit note are entered at those same later steps.
			f("workflow_state", "Status", "Link", options="Workflow State", read_only=1,
				allow_on_submit=1, in_list_view=1, in_standard_filter=1, no_copy=1),
			section("sb_trace", "Traceability (pulled from the serial)"),
			f("pump_model", "Pump Model", "Link", options="Pump Model", read_only=1),
			f("heat_no", "Heat No", "Link", options="Batch", read_only=1),
			column("cb2"),
			f("winding_batch", "Winding Batch", "Link", options="Batch", read_only=1),
			f("root_cause", "Root Cause", "Select", options=ROOT_CAUSES),
			section("sb_parts", "Claimed Parts"),
			f("defective_parts", "Defective Parts", "Table", options="Claim Part Row"),
			f("claim_amount", "Claim Amount", "Currency", read_only=1, in_list_view=1),
			column("cb3"),
			f("approved_amount", "Approved Amount", "Currency", allow_on_submit=1),
			f("credit_note", "Credit Note", "Link", options="Sales Invoice", allow_on_submit=1),
			section("sb_evidence", "Evidence"),
			f("technician_report", "Technician Report", "Text"),
			f("defect_photo", "Defect Photo", "Attach Image"),
			column("cb4"),
			f("remarks", "Remarks", "Small Text", allow_on_submit=1),
			f("settled_on", "Settled On", "Date", read_only=1, allow_on_submit=1),
			f("amended_from", "Amended From", "Link", options="Kumar Warranty Claim", read_only=1,
				no_copy=1, print_hide=1),
		],
		autoname="naming_series:",
		naming_rule="By \"Naming Series\" field",
		is_submittable=1,
		title_field="serial_no",
		description="Dealer asks for warranty settlement. Heat and winding batch ride along, which is what makes batch defect analysis possible.",
		permissions=[
			perm("System Manager", delete=1, submit=1, cancel=1, amend=1),
			perm("Warranty Approver", delete=1, submit=1, cancel=1, amend=1),
			perm("Service Manager", submit=1, cancel=1, amend=1),
			perm("Quality Engineer", create=0, write=1, submit=1),
			perm("Dealer", create=1, write=1, submit=1, export=0),
			perm("Accounts User", create=0, write=1, submit=1),
		],
	)


# ------------------------------------------------------------ traceability


def heat_spectro_reading():
	make_doctype(
		"Heat Spectro Reading",
		[
			f("element", "Element", "Select", options="C\nSi\nMn\nS\nP\nCr\nCu\nNi\nMg",
				in_list_view=1, reqd=1),
			f("value_pct", "Value %", "Float", precision="4", in_list_view=1),
			f("spec_min", "Spec Min", "Float", precision="4", in_list_view=1),
			f("spec_max", "Spec Max", "Float", precision="4", in_list_view=1),
			f("within_spec", "Within Spec", "Check", read_only=1, in_list_view=1),
		],
		istable=1,
	)


def heat_record():
	make_doctype(
		"Heat Record",
		[
			f("naming_series", "Series", "Select", options="HTR-.YY..MM.-.####",
				default="HTR-.YY..MM.-.####", reqd=1, print_hide=1),
			f("heat_no", "Heat No", reqd=1, unique=1, in_list_view=1, bold=1,
				description="Also created as a Batch so castings can carry it"),
			f("heat_date", "Heat Date", "Date", reqd=1, default="Today", in_list_view=1),
			f("furnace", "Furnace", "Link", options="Workstation"),
			column("cb1"),
			f("shift", "Shift", "Select", options="A\nB\nC", default="A"),
			f("charge_weight_kg", "Charge Weight (kg)", "Float"),
			f("tapping_temperature_c", "Tapping Temp (C)", "Float", default="1500"),
			f("status", "Status", "Select",
				options="Draft\nApproved for Pouring\nRejected", default="Draft",
				in_list_view=1, in_standard_filter=1),
			section("sb_spectro", "Spectrometer Analysis (before pouring)"),
			f("target_grade", "Target Grade", "Select", options="FG 200\nFG 260\nSG 500-7\nOther",
				default="FG 200"),
			f("grade_achieved", "Grade Achieved", "Select", options="\nFG 200\nFG 260\nSG 500-7\nOther"),
			column("cb2"),
			f("carbon_equivalent", "Carbon Equivalent", "Float", read_only=1, precision="3"),
			f("all_within_spec", "All Elements Within Spec", "Check", read_only=1),
			section("sb_rows"),
			f("spectro_readings", "Spectro Readings", "Table", options="Heat Spectro Reading"),
			section("sb_lab", "Lab Approval"),
			f("lab_approved_by", "Approved By", "Link", options="User", read_only=1),
			f("lab_approved_on", "Approved On", "Datetime", read_only=1),
			column("cb3"),
			f("override_reason", "Out-of-Spec Override Reason", "Small Text",
				description="Required to approve a heat with any element out of spec"),
			f("remarks", "Remarks", "Small Text"),
		],
		autoname="naming_series:",
		naming_rule="By \"Naming Series\" field",
		title_field="heat_no",
		description="One furnace melt. Chemistry is checked before pouring - this is the root of backward traceability.",
		permissions=[
			perm("System Manager", delete=1, submit=1, cancel=1),
			perm("Quality Engineer", delete=1),
			perm("Production Manager"),
			perm("Foundry Operator", delete=0),
			perm("Service Manager", create=0, write=0),
		],
	)


def winding_batch_record():
	make_doctype(
		"Winding Batch Record",
		[
			f("naming_series", "Series", "Select", options="WDR-.YY..MM.-.####",
				default="WDR-.YY..MM.-.####", reqd=1, print_hide=1),
			f("batch_no", "Winding Batch No", reqd=1, unique=1, in_list_view=1, bold=1),
			f("winding_date", "Winding Date", "Date", reqd=1, default="Today", in_list_view=1),
			f("machine", "Machine", "Link", options="Workstation"),
			f("operator", "Operator", "Link", options="Employee"),
			column("cb1"),
			f("pump_model", "Pump Model", "Link", options="Pump Model", in_list_view=1),
			f("copper_wire_batch", "Copper Wire Batch", "Link", options="Batch"),
			f("wire_gauge_swg", "Wire Gauge (SWG)"),
			f("turns_per_coil", "Turns per Coil", "Int"),
			section("sb_cure", "Varnish & Cure"),
			f("varnish_batch", "Varnish Batch", "Link", options="Batch"),
			f("oven_temp_c", "Oven Temp (C)", "Float"),
			column("cb2"),
			f("cure_duration_min", "Cure Duration (min)", "Int"),
			section("sb_test", "Electrical Test"),
			f("ir_test_mohm", "IR Test (Mohm)", "Float"),
			f("hipot_test_kv", "HiPot Test (kV)", "Float"),
			column("cb3"),
			f("winding_resistance_ohm", "Winding Resistance (ohm)", "Float"),
			section("sb_qty", "Output"),
			f("qty_produced", "Qty Produced", "Int", in_list_view=1),
			f("qty_passed", "Qty Passed", "Int"),
			column("cb4"),
			f("qty_rejected", "Qty Rejected", "Int"),
			f("rejection_reason", "Rejection Reason", "Small Text"),
		],
		autoname="naming_series:",
		naming_rule="By \"Naming Series\" field",
		title_field="batch_no",
		description="One stator winding lot. Carried onto every serial built from it.",
		permissions=[
			perm("System Manager", delete=1),
			perm("Quality Engineer", delete=1),
			perm("Production Manager"),
			perm("Service Manager", create=0, write=0),
		],
	)


def test_duty_point():
	make_doctype(
		"Test Duty Point",
		[
			f("head_m", "Head (m)", "Float", in_list_view=1),
			f("discharge_lpm", "Discharge (LPM)", "Float", in_list_view=1),
			f("input_power_kw", "Input Power (kW)", "Float", in_list_view=1),
			f("current_a", "Current (A)", "Float", in_list_view=1),
			f("speed_rpm", "Speed (RPM)", "Int"),
			f("efficiency_pct", "Efficiency %", "Float", in_list_view=1),
			f("is_duty_point", "Duty Point", "Check", in_list_view=1),
		],
		istable=1,
	)


def pump_test_certificate():
	make_doctype(
		"Pump Test Certificate",
		[
			f("naming_series", "Series", "Select", options="TC-.YY.-.######",
				default="TC-.YY.-.######", reqd=1, print_hide=1),
			f("serial_no", "Serial No", "Link", options="Serial No", reqd=1, in_list_view=1, bold=1),
			f("pump_model", "Pump Model", "Link", options="Pump Model", read_only=1, in_list_view=1),
			f("test_date", "Test Date", "Datetime", reqd=1, default="now", in_list_view=1),
			column("cb1"),
			f("test_bench", "Test Bench", "Link", options="Workstation"),
			f("tested_by", "Tested By", "Link", options="Employee"),
			f("bis_standard_ref", "BIS Standard Ref"),
			section("sb_supply", "Supply"),
			f("supply_voltage_v", "Supply Voltage (V)", "Float", default="415"),
			f("frequency_hz", "Frequency (Hz)", "Float", default="50"),
			column("cb2"),
			f("no_load_current_a", "No Load Current (A)", "Float"),
			f("full_load_current_a", "Full Load Current (A)", "Float"),
			section("sb_duty", "Duty Points"),
			f("duty_points", "Duty Points", "Table", options="Test Duty Point"),
			section("sb_elec", "Electrical & Mechanical Tests"),
			f("insulation_resistance_mohm", "Insulation Resistance (Mohm)", "Float"),
			f("hipot_voltage_kv", "HiPot Voltage (kV)", "Float"),
			f("hipot_result", "HiPot Result", "Select", options="\nPass\nFail"),
			column("cb3"),
			f("hydrostatic_test_pressure", "Hydrostatic Pressure (kg/cm2)", "Float"),
			f("hydrostatic_result", "Hydrostatic Result", "Select", options="\nPass\nFail"),
			column("cb3b"),
			f("vibration_mm_s", "Vibration (mm/s)", "Float"),
			f("noise_db", "Noise (dB)", "Float"),
			section("sb_result", "Result"),
			f("overall_result", "Overall Result", "Select", options="Pass\nFail\nRework",
				default="Pass", reqd=1, in_list_view=1, in_standard_filter=1),
			column("cb4"),
			f("remarks", "Remarks", "Small Text"),
			f("amended_from", "Amended From", "Link", options="Pump Test Certificate", read_only=1,
				no_copy=1, print_hide=1),
		],
		autoname="naming_series:",
		naming_rule="By \"Naming Series\" field",
		is_submittable=1,
		title_field="serial_no",
		description="Per-unit test record. On submit it stamps QC status on the Serial No, which gates dispatch.",
		permissions=[
			perm("System Manager", delete=1, submit=1, cancel=1, amend=1),
			perm("Quality Engineer", delete=1, submit=1, cancel=1, amend=1),
			perm("Production Manager", submit=1),
			perm("Service Manager", create=0, write=0),
			perm("Service Technician", create=0, write=0),
			perm("Dealer", create=0, write=0, export=0),
		],
	)
