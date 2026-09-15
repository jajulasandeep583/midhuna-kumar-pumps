<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ __("Home") }}</div>
      </template>
    </LayoutHeader>

    <div class="px-5 py-6">
      <!-- the tiles used to flash "-" on every load, and stay "-" for good if
           the call failed, with nothing to say why -->
      <div v-if="summary.error" class="mb-6 rounded-xl border border-red-200 bg-red-50 p-5 text-center">
        <p class="font-medium text-red-800">{{ __("Your summary could not load.") }}</p>
        <ErrorMessage class="mt-1" :message="summary.error" />
        <Button class="mt-3" variant="solid" theme="blue" :label="__('Try again')" @click="summary.reload()" />
      </div>

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
            <span v-if="summary.loading && !summary.data"
                  class="inline-block h-7 w-10 animate-pulse rounded bg-black/10"></span>
            <template v-else>{{ s.value }}</template>
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

      <!-- the visits booked on this dealer's pumps, so the dealer can tell the
           customer to be home - previously this fact lived only inside each
           ticket's thread -->
      <template v-if="(visits.data || []).length">
        <div class="mb-2 mt-8 flex items-baseline gap-3">
          <span class="text-xs font-semibold uppercase tracking-wider text-ink-gray-4">
            {{ __("Upcoming visits") }}
          </span>
          <span class="text-xs text-ink-gray-5">
            {{ __("KUMAR is coming to these pumps") }}
          </span>
        </div>
        <div class="overflow-x-auto rounded-xl border bg-surface-white">
          <table class="w-full text-sm">
            <tbody>
              <!-- the whole row opens the conversation the booking lives on -->
              <tr
                v-for="v in visits.data"
                :key="v.name"
                class="border-t first:border-t-0"
                :class="v.ticket ? 'cursor-pointer hover:bg-surface-gray-1' : ''"
                @click="v.ticket && router.push({ name: 'TicketCustomer', params: { ticketId: v.ticket } })"
              >
                <td class="whitespace-nowrap px-4 py-2.5 font-medium tabular-nums text-ink-gray-8">
                  {{ v.visit_date }}
                </td>
                <td class="px-4 py-2.5">
                  <div class="text-ink-gray-8">{{ v.technician }}</div>
                  <a v-if="v.technician_mobile" class="text-xs tabular-nums text-ink-blue-6 hover:underline"
                     :href="`tel:${v.technician_mobile}`" @click.stop>{{ v.technician_mobile }}</a>
                </td>
                <td class="px-4 py-2.5">
                  <div class="tabular-nums text-ink-gray-7">{{ v.serial_no }}</div>
                  <div class="text-xs text-ink-gray-5">{{ v.customer }}</div>
                </td>
                <td class="whitespace-nowrap px-4 py-2.5 text-right">
                  <Badge :theme="v.is_chargeable ? 'orange' : 'green'"
                         :label="chargeLabel(v.is_chargeable)" />
                  <span v-if="v.ticket" class="ml-2 text-xs text-ink-blue-6">{{ __("Open") }} ›</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { Badge, Button, ErrorMessage, createResource } from "frappe-ui";
import { chargeLabel } from "@/utils/kumarTypes";
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
const visits = createResource({ url: "kumar_service.portal_api.my_visits", auto: true });

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
    query: { warranty: "In Warranty" },
    card: "border-green-200 bg-green-50 hover:border-green-300",
    strong: "text-green-800",
    muted: "text-green-700",
  },
  {
    label: __("Expiring in {0} days", [String(summary.data?.expiring_soon_days ?? 30)]),
    value: summary.data?.expiring ?? "-",
    // the one number on this screen that is a to-do list - so the click lands
    // on What I Sold ALREADY filtered to exactly these pumps
    hint: __("Worth a phone call"),
    icon: LucideClock,
    to: "KumarPumps",
    query: { warranty: "Expiring Soon" },
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
