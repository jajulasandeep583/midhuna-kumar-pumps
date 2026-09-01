<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ __("Home") }}</div>
      </template>
    </LayoutHeader>

    <div class="px-5 py-6">
      <!-- Colour that means something: green is healthy, amber is a warranty
           about to lapse, blue is work sitting with KUMAR. A dealer should be
           able to read this strip in one glance from across a counter. -->
      <div class="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <button
          v-for="s in stats"
          :key="s.label"
          class="rounded-xl border p-4 text-left transition hover:shadow-md"
          :class="s.card"
          @click="s.to && router.push({ name: s.to, query: s.query })"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="text-xs font-medium" :class="s.muted">{{ s.label }}</div>
            <component :is="s.icon" class="size-4 shrink-0" :class="s.muted" />
          </div>
          <div class="mt-2 text-3xl font-semibold tabular-nums" :class="s.strong">
            {{ s.value }}
          </div>
          <div class="mt-1 text-xs" :class="s.muted">{{ s.hint }}</div>
        </button>
      </div>

      <div class="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-gray-4">
        {{ __("What do you need to do?") }}
      </div>
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <button
          v-for="a in actions"
          :key="a.name"
          class="flex items-start gap-3 rounded-xl border border-outline-gray-2 bg-surface-white p-4 text-left transition hover:-translate-y-0.5 hover:shadow-md"
          @click="router.push({ name: a.name })"
        >
          <span class="mt-0.5 grid size-9 shrink-0 place-items-center rounded-lg" :class="a.tint">
            <component :is="a.icon" class="size-4.5" />
          </span>
          <div>
            <div class="text-sm font-medium text-ink-gray-8">{{ a.label }}</div>
            <div class="mt-0.5 text-xs text-ink-gray-5">{{ a.hint }}</div>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { createResource } from "frappe-ui";
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";
import LucideFilePlus from "~icons/lucide/file-plus";
import LucideMessageSquare from "~icons/lucide/message-square";
import LucideShieldCheck from "~icons/lucide/shield-check";
import LucideList from "~icons/lucide/list";
import LucideClock from "~icons/lucide/clock";
import LucideTicket from "~icons/lucide/ticket";

const router = useRouter();
const summary = createResource({ url: "kumar_service.portal_api.my_summary", auto: true });

const stats = computed(() => [
  {
    label: __("Pumps you sold"),
    value: summary.data?.pumps ?? "-",
    hint: __("All time"),
    icon: LucideList,
    to: "KumarPumps",
    card: "border-outline-gray-2 bg-surface-white hover:border-outline-gray-3",
    strong: "text-ink-gray-9",
    muted: "text-ink-gray-5",
  },
  {
    label: __("In warranty"),
    value: summary.data?.in_warranty ?? "-",
    hint: __("Still covered"),
    icon: LucideShieldCheck,
    to: "KumarPumps",
    card: "border-green-200 bg-green-50 hover:border-green-300",
    strong: "text-green-800",
    muted: "text-green-700",
  },
  {
    label: __("Expiring in 45 days"),
    value: summary.data?.expiring ?? "-",
    // the one number on this screen that is a to-do list
    hint: __("Worth a phone call"),
    icon: LucideClock,
    to: "KumarPumps",
    card: "border-amber-200 bg-amber-50 hover:border-amber-300",
    strong: "text-amber-800",
    muted: "text-amber-700",
  },
  {
    label: __("Open with KUMAR"),
    value: summary.data?.open_tickets ?? "-",
    hint: __("Complaints and claims"),
    icon: LucideTicket,
    to: "TicketsCustomer",
    card: "border-blue-200 bg-blue-50 hover:border-blue-300",
    strong: "text-blue-800",
    muted: "text-blue-700",
  },
]);

const actions = [
  {
    name: "KumarRegister",
    label: __("Register a Sale"),
    hint: __("The warranty starts from the registration"),
    icon: LucideFilePlus,
    tint: "bg-blue-50 text-blue-700",
  },
  {
    name: "KumarComplaintNew",
    label: __("Raise a Request"),
    hint: __("A fault, an installation, a part"),
    icon: LucideMessageSquare,
    tint: "bg-amber-50 text-amber-700",
  },
  {
    name: "KumarClaimNew",
    label: __("Warranty Claim"),
    hint: __("Ask KUMAR to settle a failure"),
    icon: LucideShieldCheck,
    tint: "bg-green-50 text-green-700",
  },
];
</script>
