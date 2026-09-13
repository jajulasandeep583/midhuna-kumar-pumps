// The kind of ticket, at a glance. One colour per kind, used wherever a
// ticket is named: the list, the header, the panel.
import { __ } from "@/translation";

export const TICKET_TYPE_THEME: Record<string, string> = {
  Complaint: "orange",
  "Warranty Claim": "purple",
  Installation: "blue",
  "Spare Part": "gray",
  Enquiry: "green",
  "Service Visit": "blue",
  "Preventive Maintenance": "blue",
  AMC: "blue",
};
export function ticketTypeTheme(type?: string | null): string {
  return (type && TICKET_TYPE_THEME[type]) || "gray";
}
export function ticketTypeLabel(type?: string | null): string {
  return type ? __(type) : __("Untyped");
}
// Warranty state, one colour everywhere. The desk and the dealer portal each
// carried their own copy of this and they disagreed - "Expired" was grey on
// What I Sold and red on Raise for a Pump: the same fact in two colours. Both
// vocabularies live here, the three-state one the portal uses (In Warranty /
// Expiring Soon / Expired) and the two-state one a ticket carries.
export const WARRANTY_THEME: Record<string, string> = {
  "In Warranty": "green",
  "Expiring Soon": "orange",
  Expired: "red",
  "Out of Warranty": "red",
  "Not Registered": "gray",
};
export function warrantyStateTheme(state?: string | null): string {
  return (state && WARRANTY_THEME[state]) || "gray";
}
export function warrantyTheme(w?: string | null): string {
  return warrantyStateTheme(w);
}

// Rupees, the one way. Copy-pasted into three pages before this.
export function money(v?: number | null): string {
  return "₹" + Math.round(v || 0).toLocaleString("en-IN");
}

// Whether a visit costs the customer anything. The staff boards said "Free"
// and the dealer's home said "Free - warranty" for the identical fact.
export function chargeLabel(chargeable?: boolean | number | null): string {
  return chargeable ? __("Chargeable") : __("Free");
}
