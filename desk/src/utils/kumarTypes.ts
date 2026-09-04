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
export function warrantyTheme(w?: string | null): string {
  return w === "In Warranty" ? "green" : w === "Out of Warranty" ? "red" : "gray";
}
