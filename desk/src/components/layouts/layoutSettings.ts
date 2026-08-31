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
import LucideLayoutDashboard from "~icons/lucide/layout-dashboard";
import { OrganizationsIcon } from "../icons";
import PhoneIcon from "../icons/PhoneIcon.vue";
import LucideHome from "~icons/lucide/home";
import { __ } from "@/translation";

/**
 * Shared rather than local to Sidebar.vue: the command palette opens it too, and
 * the palette is the discovery surface for the shortcut system.
 */
export const showShortcutsModal = ref(false);

export const agentPortalSidebarOptions = [
  {
    label: __("Home"),
    icon: LucideHome,
    to: "Home",
  },
  {
    label: __("Dashboard"),
    icon: LucideLayoutDashboard,
    to: "Dashboard"
  },
  {
    label: __("Tickets"),
    icon: LucideTicket,
    to: "TicketsAgent",
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
    label: __("Raise a Complaint"),
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
