import LucideSearchCheck from "~icons/lucide/search-check";
import LucideIndianRupee from "~icons/lucide/indian-rupee";
import LucideGauge from "~icons/lucide/gauge";
import LucideCalendarCheck from "~icons/lucide/calendar-check";
import LucideHome from "~icons/lucide/home";
import LucideFilePlus from "~icons/lucide/file-plus";
import LucideList from "~icons/lucide/list";
import LucideMessageSquare from "~icons/lucide/message-square";
import LucideShieldCheck from "~icons/lucide/shield-check";
import LucidePhone from "~icons/lucide/phone";
import { ref } from "vue";
import LucideBookOpen from "~icons/lucide/book-open";
import LucideUsers from "~icons/lucide/users";
import LucideTicket from "~icons/lucide/ticket";
import { OrganizationsIcon } from "../icons";
import PhoneIcon from "../icons/PhoneIcon.vue";
import { __ } from "@/translation";

/**
 * Shared rather than local to Sidebar.vue: the command palette opens it too, and
 * the palette is the discovery surface for the shortcut system.
 */
export const showShortcutsModal = ref(false);

// Ordered the way a KUMAR service person moves through a day, top to bottom:
// the Command Centre is this product's front door and the landing screen, then
// the queue, creating work, looking a pump up, the claims and visits desks,
// and finally the personal and reference screens. (The Helpdesk "Dashboard"
// analytics page is intentionally not here - it needs the Agent Manager role
// none of the service roles carry, so it only ever threw a permission error.)
export const agentPortalSidebarOptions = [
  {
    label: __("Command Centre"),
    icon: LucideGauge,
    to: "KumarManage",
  },
  {
    label: __("Tickets"),
    icon: LucideTicket,
    to: "TicketsAgent",
  },
  {
    label: __("Raise for a Pump"),
    icon: LucideFilePlus,
    to: "KumarRaise",
  },
  {
    label: __("Pump Lookup"),
    icon: LucideSearchCheck,
    to: "KumarLookup",
  },
  {
    label: __("Claims"),
    icon: LucideIndianRupee,
    to: "KumarClaims",
  },
  {
    label: __("Visits"),
    icon: LucideCalendarCheck,
    to: "KumarVisits",
  },
  {
    label: __("Home"),
    icon: LucideHome,
    to: "Home",
  },
  {
    label: __("Knowledge Base"),
    icon: LucideBookOpen,
    to: "AgentKnowledgeBase",
  },
  {
    label: "Customers",
    icon: OrganizationsIcon,
    to: "CustomerList",
  },
  {
    label: __("Contacts"),
    icon: LucideUsers,
    to: "ContactList",
  },
  {
    label: __("Call Logs"),
    icon: PhoneIcon,
    to: "CallLogs",
  },
];

// A dealer's whole job, in the one rail the customer portal already has.
// These used to live in a second sidebar of our own, which meant the desk
// showed two rails side by side - the app's and ours.
export const customerPortalSidebarOptions = [
  {
    label: __("Home"),
    icon: LucideHome,
    to: "KumarHome",
  },
  {
    label: __("Register a Sale"),
    icon: LucideFilePlus,
    to: "KumarRegister",
  },
  {
    label: __("What I Sold"),
    icon: LucideList,
    to: "KumarPumps",
  },
  {
    label: __("Pump Lookup"),
    icon: LucideSearchCheck,
    to: "KumarDealerLookup",
  },
  {
    label: __("Raise a Request"),
    icon: LucideMessageSquare,
    to: "KumarComplaint",
  },
  {
    label: __("Warranty Claim"),
    icon: LucideShieldCheck,
    to: "KumarClaim",
  },
  {
    label: __("My Tickets"),
    icon: LucideTicket,
    to: "TicketsCustomer",
  },
  {
    label: __("Contact KUMAR"),
    icon: LucidePhone,
    to: "KumarContact",
  },
  {
    label: __("Knowledge Base"),
    icon: LucideBookOpen,
    to: "CustomerKnowledgeBase",
  },
];
