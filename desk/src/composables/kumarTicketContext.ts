import { createResource } from "frappe-ui";

// One kumar_service.staff_api.ticket_context resource PER TICKET, shared by
// every component that shows the job behind a ticket (the KUMAR panel in the
// details tab, the claim actions in the ticket header). Shared on purpose:
// a claim decided in the header must update the panel in the same breath -
// two fetches of the same context that could disagree is how the user ends
// up staring at an Approve button on a claim that is already approved.
const registry = new Map<string, any>();

export function kumarTicketContext(ticketName: string, { fresh = false } = {}) {
  const name = String(ticketName || "");
  if (!name) return null;
  let res = registry.get(name);
  if (!res) {
    res = createResource({
      url: "kumar_service.staff_api.ticket_context",
      params: { ticket: name },
      auto: true,
    });
    registry.set(name, res);
  } else if (fresh && !res.loading) {
    // a revisit after navigating away: the shared instance survives, so the
    // caller that owns the mount asks for current data once
    res.reload();
  }
  return res;
}
