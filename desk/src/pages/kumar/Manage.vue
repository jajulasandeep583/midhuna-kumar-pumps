<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ __("Command Centre") }}</div>
      </template>
      <template #right-header>
        <Button variant="ghost" :label="__('Refresh')" @click="d.reload()" />
      </template>
    </LayoutHeader>

    <div v-if="d.loading && !d.data" class="py-16 text-center text-ink-gray-5">
      {{ __("Loading...") }}
    </div>

    <div v-else-if="d.data" class="px-5 py-5">
      <!-- what needs you, before anything else ---------------------------- -->
      <div class="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <button
          v-for="k in kpis"
          :key="k.label"
          class="rounded-xl border p-4 text-left transition hover:shadow-md"
          :class="k.card"
          @click="k.to && router.push({ name: k.to })"
        >
          <div class="flex items-start justify-between gap-2">
            <span class="text-xs font-medium" :class="k.muted">{{ k.label }}</span>
            <component :is="k.icon" class="size-4 shrink-0" :class="k.muted" />
          </div>
          <div class="mt-2 text-3xl font-semibold tabular-nums" :class="k.strong">{{ k.value }}</div>
          <div class="mt-1 text-xs" :class="k.muted">{{ k.hint }}</div>
        </button>
      </div>

      <div class="grid gap-5 lg:grid-cols-3">
        <!-- needs you ---------------------------------------------------- -->
        <div class="lg:col-span-2">
          <div class="mb-2 flex items-baseline gap-3">
            <h2 class="text-sm font-semibold text-ink-gray-8">{{ __("Needs you") }}</h2>
            <span class="text-xs text-ink-gray-5">{{ __("Oldest first") }}</span>
          </div>
          <div class="overflow-hidden rounded-lg border bg-surface-white">
            <div
              v-if="!needsYou.length"
              class="py-10 text-center text-sm text-ink-gray-5"
            >
              {{ __("Nothing is past due. ") }}
            </div>
            <table v-else class="w-full text-sm">
              <thead class="bg-surface-gray-2 text-xs uppercase tracking-wide text-ink-gray-5">
                <tr>
                  <th class="px-3 py-2 text-left font-medium">{{ __("What") }}</th>
                  <th class="px-3 py-2 text-left font-medium">{{ __("Dealer") }}</th>
                  <th class="px-3 py-2 text-left font-medium">{{ __("Raised") }}</th>
                  <th class="px-3 py-2 text-right font-medium"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in needsYou" :key="r.name" class="border-t hover:bg-surface-gray-1">
                  <td class="px-3 py-2">
                    <div class="font-medium text-ink-gray-8">{{ r.what }}</div>
                    <div class="text-xs tabular-nums text-ink-gray-5">{{ r.serial_no }}</div>
                  </td>
                  <td class="px-3 py-2 text-ink-gray-7">
                    <div>{{ r.dealer }}</div>
                    <div class="text-xs text-ink-gray-5">{{ r.customer }}</div>
                  </td>
                  <td class="px-3 py-2 tabular-nums text-ink-gray-7">
                    {{ String(r.reported_on).slice(0, 10) }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-2 text-right">
                    <Badge :theme="r.warranty ? 'green' : 'orange'"
                           :label="r.warranty ? __('Free') : __('Chargeable')" />
                    <Button class="ml-2" variant="subtle" theme="blue" :label="__('Schedule')"
                            @click="router.push({ name: 'KumarVisits' })" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- the network ------------------------------------------------ -->
          <h2 class="mb-2 mt-8 text-sm font-semibold text-ink-gray-8">
            {{ __("The dealer network") }}
          </h2>
          <div class="overflow-x-auto rounded-lg border bg-surface-white">
            <table class="w-full text-sm">
              <thead class="bg-surface-gray-2 text-xs uppercase tracking-wide text-ink-gray-5">
                <tr>
                  <th class="px-3 py-2 text-left font-medium">{{ __("Outlet") }}</th>
                  <th class="px-3 py-2 text-right font-medium">{{ __("Pumps") }}</th>
                  <th class="px-3 py-2 text-right font-medium">{{ __("Open") }}</th>
                  <th class="px-3 py-2 text-right font-medium">{{ __("Past due") }}</th>
                  <th class="px-3 py-2 text-right font-medium">{{ __("Claims") }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="n in d.data.network" :key="n.dealer" class="border-t hover:bg-surface-gray-1">
                  <td class="px-3 py-2">
                    <div class="font-medium text-ink-gray-8">{{ n.label }}</div>
                    <div class="text-xs text-ink-gray-5">
                      {{ [n.city, n.state].filter(Boolean).join(", ") }}
                      <span v-if="n.own" class="ml-1 text-ink-blue-3">{{ __("KUMAR branch") }}</span>
                    </div>
                  </td>
                  <td class="px-3 py-2 text-right tabular-nums text-ink-gray-7">{{ n.pumps }}</td>
                  <td class="px-3 py-2 text-right tabular-nums text-ink-gray-7">{{ n.open }}</td>
                  <td class="px-3 py-2 text-right tabular-nums">
                    <span :class="n.breached ? 'font-semibold text-ink-red-3' : 'text-ink-gray-5'">
                      {{ n.breached }}
                    </span>
                  </td>
                  <td class="px-3 py-2 text-right tabular-nums text-ink-gray-7">
                    {{ n.claims }}
                    <span v-if="n.claim_value" class="block text-xs text-ink-gray-5">
                      {{ money(n.claim_value) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- side column -------------------------------------------------- -->
        <div>
          <h2 class="mb-2 text-sm font-semibold text-ink-gray-8">{{ __("Money on the table") }}</h2>
          <div class="rounded-lg border bg-surface-white p-4">
            <div v-for="m in moneyRows" :key="m.label" class="flex items-baseline justify-between border-b py-2 last:border-b-0">
              <span class="text-sm" :class="m.tone">{{ m.label }}</span>
              <span class="text-right">
                <span class="block font-semibold tabular-nums text-ink-gray-9">{{ m.value }}</span>
                <span class="text-xs tabular-nums text-ink-gray-5">{{ m.count }}</span>
              </span>
            </div>
          </div>

          <h2 class="mb-2 mt-6 text-sm font-semibold text-ink-gray-8">{{ __("Warranty cover") }}</h2>
          <div class="rounded-lg border bg-surface-white p-4">
            <div class="mb-3 flex h-2.5 overflow-hidden rounded-full bg-surface-gray-3">
              <div class="bg-green-500" :style="{ width: pct(d.data.warranty.in_warranty) }"></div>
              <div class="bg-amber-400" :style="{ width: pct(d.data.warranty.expiring) }"></div>
              <div class="bg-surface-gray-5" :style="{ width: pct(d.data.warranty.expired) }"></div>
            </div>
            <div v-for="w in warrantyRows" :key="w.label" class="flex items-center justify-between py-1 text-sm">
              <span class="flex items-center gap-2 text-ink-gray-7">
                <span class="size-2 rounded-full" :class="w.dot"></span>{{ w.label }}
              </span>
              <span class="tabular-nums text-ink-gray-8">{{ w.value }}</span>
            </div>
          </div>

          <h2 class="mb-2 mt-6 text-sm font-semibold text-ink-gray-8">
            {{ __("What keeps breaking") }}
          </h2>
          <div class="rounded-lg border bg-surface-white p-4">
            <div v-for="f in d.data.top_faults" :key="f.label" class="mb-2.5 last:mb-0">
              <div class="mb-1 flex items-baseline justify-between text-sm">
                <span class="text-ink-gray-7">{{ __(f.label) }}</span>
                <span class="tabular-nums text-ink-gray-5">{{ f.count }}</span>
              </div>
              <div class="h-1.5 overflow-hidden rounded-full bg-surface-gray-3">
                <div class="h-full rounded-full bg-blue-500" :style="{ width: faultPct(f.count) }"></div>
              </div>
            </div>
          </div>

          <h2 class="mb-2 mt-6 text-sm font-semibold text-ink-gray-8">{{ __("Visits booked") }}</h2>
          <div class="rounded-lg border bg-surface-white p-4 text-sm">
            <div v-if="!d.data.visits.length" class="text-ink-gray-5">
              {{ __("Nothing booked.") }}
              <router-link class="text-ink-blue-3" :to="{ name: 'KumarVisits' }">
                {{ __("Schedule one") }}
              </router-link>
            </div>
            <div v-for="v in d.data.visits" :key="v.name" class="flex justify-between border-b py-1.5 last:border-b-0">
              <span class="text-ink-gray-7">{{ v.technician }}</span>
              <span class="tabular-nums text-ink-gray-5">{{ v.visit_date }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { Badge, Button, createResource } from "frappe-ui";
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";
import LucideAlertTriangle from "~icons/lucide/alert-triangle";
import LucideInbox from "~icons/lucide/inbox";
import LucideIndianRupee from "~icons/lucide/indian-rupee";
import LucideCalendarCheck from "~icons/lucide/calendar-check";

const router = useRouter();
const d = createResource({ url: "kumar_service.staff_api.manager_dashboard", auto: true });

function money(v: number) {
  return "₹" + Math.round(v || 0).toLocaleString("en-IN");
}

const kpis = computed(() => {
  const w = d.data?.work || {};
  const m = d.data?.money || {};
  return [
    {
      label: __("Past due"),
      value: w.breached ?? "-",
      hint: __("Resolution time already gone"),
      icon: LucideAlertTriangle,
      to: "KumarVisits",
      card: "border-red-200 bg-red-50 hover:border-red-300",
      strong: "text-red-800", muted: "text-red-700",
    },
    {
      label: __("Open with KUMAR"),
      value: w.open ?? "-",
      hint: __("Across the whole network"),
      icon: LucideInbox,
      to: "TicketsAgent",
      card: "border-outline-gray-2 bg-surface-white hover:border-outline-gray-3",
      strong: "text-ink-gray-9", muted: "text-ink-gray-5",
    },
    {
      label: __("Claims to decide"),
      value: m.pending_count ?? "-",
      hint: money(m.pending_value) + __(" waiting on a decision"),
      icon: LucideIndianRupee,
      card: "border-amber-200 bg-amber-50 hover:border-amber-300",
      strong: "text-amber-800", muted: "text-amber-700",
    },
    {
      label: __("Visits booked"),
      value: w.visits_booked ?? "-",
      hint: w.visits_today ? __("{0} today", [String(w.visits_today)]) : __("None today"),
      icon: LucideCalendarCheck,
      to: "KumarVisits",
      card: "border-blue-200 bg-blue-50 hover:border-blue-300",
      strong: "text-blue-800", muted: "text-blue-700",
    },
  ];
});

// breached first, then anything we have not answered at all
const needsYou = computed(() => {
  const n = d.data?.needs_you || {};
  const seen = new Set();
  return [...(n.breached || []), ...(n.unanswered || [])].filter((r: any) => {
    if (seen.has(r.name)) return false;
    seen.add(r.name);
    return true;
  }).slice(0, 8);
});

const moneyRows = computed(() => {
  const m = d.data?.money || {};
  return [
    { label: __("Waiting on a decision"), value: money(m.pending_value),
      count: __("{0} claims", [String(m.pending_count || 0)]), tone: "text-amber-700" },
    { label: __("Approved, not yet paid"), value: money(m.approved_value),
      count: __("{0} claims", [String(m.approved_count || 0)]), tone: "text-ink-gray-7" },
    { label: __("Settled, last {0} days", [String(d.data?.window_days || 30)]),
      value: money(m.settled_value),
      count: __("{0} claims", [String(m.settled_count || 0)]), tone: "text-ink-gray-7" },
  ];
});

const warrantyRows = computed(() => {
  const w = d.data?.warranty || {};
  return [
    { label: __("In warranty"), value: w.in_warranty, dot: "bg-green-500" },
    { label: __("Expiring in 45 days"), value: w.expiring, dot: "bg-amber-400" },
    { label: __("Expired"), value: w.expired, dot: "bg-surface-gray-5" },
  ];
});

function pct(n: number) {
  const t = d.data?.warranty?.total || 0;
  return t ? ((n / t) * 100).toFixed(1) + "%" : "0%";
}
function faultPct(n: number) {
  const top = d.data?.top_faults?.[0]?.count || 1;
  return ((n / top) * 100).toFixed(0) + "%";
}
</script>
