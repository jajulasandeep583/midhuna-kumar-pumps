import { useScreenSize } from "@/composables/screen";
import { canViewPersona, personaInterrupt } from "@/persona";
import { useAuthStore } from "@/stores/auth";
import { useUserStore } from "@/stores/user";
import { isCustomerPortal } from "@/utils";
import { createRouter, createWebHistory } from "vue-router";
const { isMobileView } = useScreenSize();

export const LOGIN_PAGE = "/login";

// Where the desk is mounted. One constant, because this is both the vue-router
// history base and the path every "send them to log in" redirect has to rebuild.
// It used to be the literal "/kumar-desk" in three separate places, so serving the
// app from a second path made the router treat its own routes as foreign and
// bounce you to /login?redirect-to=/kumar-desk/kumar-desk - a path that is neither.
export const DESK_BASE = "/kumar-desk";

// type the meta fields
declare module "vue-router" {
  interface RouteMeta {
    auth?: boolean;
    agent?: boolean;
    admin?: boolean;
    public?: boolean;
    onSuccessRoute?: string;
    parent?: string;
  }
}

// Pages that render inside the portal chrome; PortalRoot picks the agent or
// customer shell from the session.
const portalRoutes = [
  // Agent Portal Routes
  {
    path: "",
    redirect: "/home",
  },
  {
    path: "/home",
    name: "Home",
    component: () => import("@/pages/home/Home.vue"),
  },

  {
    path: "/tickets",
    name: "TicketsAgent",
    component: () => import("@/pages/ticket/Tickets.vue"),
  },
  {
    path: "/tickets/:ticketId",
    name: "TicketAgent",
    component: () =>
      import(`@/pages/ticket/${handleMobileView("TicketAgent")}.vue`),
    props: true,
  },
  {
    path: "/tickets/new/:templateId?",
    name: "TicketAgentNew",
    component: () => import("@/pages/ticket/TicketNew.vue"),
    props: true,
    meta: {
      onSuccessRoute: "TicketAgent",
      parent: "TicketsAgent",
    },
  },
  {
    path: "/notifications",
    name: "Notifications",
    component: () => import("@/pages/MobileNotifications.vue"),
  },
  {
    path: "/kb",
    name: "AgentKnowledgeBase",
    component: () => import("@/pages/knowledge-base/KnowledgeBaseAgent.vue"),
  },
  {
    path: "/search",
    name: "SearchAgent",
    component: () => import("@/pages/SearchAgent.vue"),
    meta: { auth: true },
  },
  {
    path: "/kb/articles/:articleId",
    name: "Article",
    component: () => import("@/pages/knowledge-base/Article.vue"),
    props: true,
  },
  {
    path: "/articles/new/:id",
    name: "NewArticle",
    component: () => import("@/pages/knowledge-base/NewArticle.vue"),
    props: true,
  },
  {
    path: "/customers",
    name: "CustomerList",
    component: () => import("@/pages/customer/Customers.vue"),
  },
  {
    path: "/customers/:id",
    name: "Customer",
    component: () => import("@/pages/customer/Customer.vue"),
    props: true,
  },
  {
    path: "/contacts",
    name: "ContactList",
    component: () => import("@/pages/contact/Contacts.vue"),
  },
  {
    path: "/contacts/:id",
    name: "Contact",
    component: () => import("@/pages/contact/Contact.vue"),
    props: true,
  },
  {
    path: "/agents",
    name: "AgentList",
    redirect: "/tickets",
  },
  {
    path: "/teams",
    name: "Teams",
    redirect: "/tickets",
  },
  {
    path: "/teams/:teamId",
    name: "Team",
    redirect: "/tickets",
  },
  {
    path: "/dashboard",
    name: "Dashboard",
    component: () => import("@/pages/dashboard/Dashboard.vue"),
  },
  {
    path: "/call-logs",
    name: "CallLogs",
    component: () => import("@/pages/call-logs/CallLogs.vue"),
  },

  // Customer Portal Routes
  {
    path: "/my-tickets",
    name: "TicketsCustomer",
    component: () => import("@/pages/ticket/Tickets.vue"),
    meta: {
      public: true,
      auth: true,
    },
  },
  {
    path: "/my-tickets/:ticketId",
    name: "TicketCustomer",
    component: () => import("@/pages/ticket/TicketCustomer.vue"),
    meta: {
      public: true,
      auth: true,
    },
    props: true,
  },
  {
    // A dealer raising a ticket is always raising it about a pump. The stock
    // form asks for a subject and nothing else, which produces a ticket nobody
    // can act on - no serial, no warranty position, no dealer. Send them to the
    // complaint form, which asks the questions that matter and files a real
    // Service Request behind it.
    path: "/my-tickets/new",
    name: "TicketNew",
    redirect: { name: "KumarComplaint" },
    meta: { public: true, auth: true },
  },
  // ------------------------------------------------- KUMAR dealer routes
  //
  // Everything a dealer does, behind one sidebar, inside the desk. These used to
  // be seven tabs on a separate website; the dealer should not have to know
  // there were ever two systems.
  //
  // They are children of one shell so the rail is mounted once and does not
  // rebuild - and every one of them calls kumar_service.portal_api, which is
  // already scoped to the caller's dealer tree, so the pages inherit that
  // scoping rather than restating it.
  // ------------------------------------------------- KUMAR dealer routes
  //
  // Flat, and deliberately not behind a shell of their own. The customer portal
  // already renders a sidebar; wrapping these in a second one put two rails on
  // the screen at once. The KUMAR items live in that rail instead - see
  // customerPortalSidebarOptions.
  //
  // Every one of them calls kumar_service.portal_api, already scoped to the
  // caller's dealer tree, so none of them restates the scoping.
  {
    path: "/dealer",
    name: "KumarHome",
    component: () => import("@/pages/kumar/Home.vue"),
    meta: { public: true, auth: true },
  },
  {
    path: "/dealer/register",
    name: "KumarRegister",
    component: () => import("@/pages/kumar/Register.vue"),
    meta: { public: true, auth: true },
  },
  {
    path: "/dealer/pumps",
    name: "KumarPumps",
    component: () => import("@/pages/kumar/MyPumps.vue"),
    meta: { public: true, auth: true },
  },
  {
    path: "/dealer/complaint",
    name: "KumarComplaint",
    component: () => import("@/pages/kumar/RaiseComplaint.vue"),
    meta: { public: true, auth: true },
  },
  {
    path: "/dealer/claim",
    name: "KumarClaim",
    component: () => import("@/pages/kumar/Claim.vue"),
    meta: { public: true, auth: true },
  },
  {
    path: "/dealer/contact",
    name: "KumarContact",
    component: () => import("@/pages/kumar/Contact.vue"),
    meta: { public: true, auth: true },
  },
  {
    path: "/kb-public",
    name: "CustomerKnowledgeBase",
    component: () => import("@/pages/knowledge-base/KnowledgeBaseCustomer.vue"),
    meta: {
      public: true,
      auth: true,
    },
  },
  {
    path: "/kb-public/:categoryId",
    name: "Articles",
    component: () => import("@/pages/knowledge-base/Articles.vue"),
    props: true,
    meta: {
      public: true,
      auth: true,
    },
  },
  {
    path: "/kb-public/articles/:articleId",
    name: "ArticlePublic",
    component: () => import("@/pages/knowledge-base/Article.vue"),
    props: true,
    meta: {
      public: true,
      auth: true,
    },
  },

  // Additonal routes
  {
    path: "/:pathMatch(.*)*",
    name: "Invalid Page",
    component: () => import("@/pages/InvalidPage.vue"),
  },
];

const routes = [
  // Renders bare — no portal chrome.
  {
    path: "/onboarding",
    name: "Persona",
    component: () => import("@/pages/PersonaForm.vue"),
    beforeEnter: () => canViewPersona(useAuthStore()) || { name: "Home" },
  },
  {
    path: "/",
    component: () => import("@/roots/PortalRoot.vue"),
    children: portalRoutes,
  },
];

const handleMobileView = (componentName: string) => {
  return isMobileView.value ? `Mobile${componentName}` : componentName;
};

export const router = createRouter({
  history: createWebHistory(`${DESK_BASE}/`),
  routes,
});

router.beforeEach(async (to, _, next) => {
  const authStore = useAuthStore();
  isCustomerPortal.value = to.meta.public || false;
  if (authStore.isLoggedIn) {
    await authStore.init();
  }

  const interrupt = personaInterrupt(to, authStore);
  if (interrupt) return next(interrupt);

  if (!authStore.isLoggedIn) {
    const redirectURL = to.fullPath !== "/" ? to.fullPath : "";

    window.location.href =
      LOGIN_PAGE +
      (redirectURL
        ? `?redirect-to=${DESK_BASE}${redirectURL}`
        : `?redirect-to=${DESK_BASE}`);
  } else if (!to.meta.public && !authStore.hasDeskAccess) {
    // a dealer has no agent desk, so send them to their own home rather than
    // to a bare ticket list - registering a pump and raising a complaint are
    // most of what they came for
    next({ name: "KumarHome" });
  } else if (to.name === "TicketAgent" && !authStore.isAgent) {
    const ticketId = to.params.ticketId;
    next({
      name: "TicketCustomer",
      params: { ticketId },
    });
  } else {
    next();
  }
});

router.afterEach(async (to) => {
  if (to.meta.public) return;
  const { users } = useUserStore();
  if (!users?.fetched) {
    await users.fetch();
  }
});
