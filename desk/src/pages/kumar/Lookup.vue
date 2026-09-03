<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ __("Pump Lookup") }}</div>
      </template>
    </LayoutHeader>

    <div class="mx-auto max-w-4xl px-5 py-6">
      <p class="mb-4 text-sm text-ink-gray-6">
        {{ __("One serial, everything about it: whose pump, how long the warranty has left, what has already gone wrong with it, and which batch it came from.") }}
      </p>

      <div class="flex items-end gap-2">
        <FormControl
          class="flex-1"
          v-model="serial"
          type="text"
          :label="__('Serial number')"
          :placeholder="__('KP-... or scan the nameplate')"
          autocomplete="off"
          @keydown.enter.prevent="look()"
        />
        <Button variant="solid" theme="blue" :loading="snap.loading" :label="__('Look up')" @click="look()" />
        <ScanButton @scanned="onScanned" />
      </div>
      <ErrorMessage v-if="notFound" class="mt-2" :message="notFound" />

      <div v-if="p" class="mt-6 space-y-4">
        <!-- the answer, before the detail --------------------------------- -->
        <div class="rounded-xl border p-5" :class="verdict.card">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div class="text-xs font-medium" :class="verdict.muted">{{ __("Warranty") }}</div>
              <div class="mt-1 text-2xl font-semibold" :class="verdict.strong">{{ verdict.headline }}</div>
              <div class="mt-1 text-sm" :class="verdict.muted">{{ verdict.detail }}</div>
            </div>
            <div class="text-right">
              <div class="font-semibold tabular-nums text-ink-gray-9">{{ p.serial_no }}</div>
              <div class="text-sm text-ink-gray-6">{{ p.pump_model }}<span v-if="p.hp"> · {{ p.hp }} HP</span></div>
              <div class="text-xs text-ink-gray-5">{{ p.category }}</div>
            </div>
          </div>

          <!-- how much of the warranty is gone -->
          <div v-if="p.is_registered && p.warranty_expiry_date" class="mt-4">
            <div class="h-2 overflow-hidden rounded-full bg-white/60">
              <div class="h-full rounded-full" :class="verdict.bar" :style="{ width: used }"></div>
            </div>
            <div class="mt-1 flex justify-between text-xs tabular-nums" :class="verdict.muted">
              <span>{{ __("Sold") }} {{ p.sale_date }}</span>
              <span>{{ __("Expires") }} {{ p.warranty_expiry_date }}</span>
            </div>
          </div>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <div class="rounded-xl border bg-surface-white p-4">
            <h3 class="mb-2 text-sm font-semibold text-ink-gray-8">{{ __("Whose pump") }}</h3>
            <dl class="space-y-1.5 text-sm">
              <div v-for="r in whose" :key="r.k" class="flex justify-between gap-3">
                <dt class="text-ink-gray-5">{{ r.k }}</dt>
                <dd class="text-right text-ink-gray-8" :class="r.mono ? 'tabular-nums' : ''">
                  <a v-if="r.tel" :href="`tel:${r.v}`" class="text-ink-blue-6 hover:underline">{{ r.v }}</a>
                  <span v-else>{{ r.v || "—" }}</span>
                </dd>
              </div>
            </dl>
          </div>

          <div class="rounded-xl border bg-surface-white p-4">
            <h3 class="mb-2 text-sm font-semibold text-ink-gray-8">{{ __("Where it came from") }}</h3>
            <dl class="space-y-1.5 text-sm">
              <div v-for="r in made" :key="r.k" class="flex justify-between gap-3">
                <dt class="text-ink-gray-5">{{ r.k }}</dt>
                <dd class="text-right tabular-nums text-ink-gray-8">{{ r.v || "—" }}</dd>
              </div>
            </dl>
          </div>
        </div>

        <!-- what has gone wrong with it before ----------------------------- -->
        <div class="rounded-xl border bg-surface-white p-4">
          <div class="mb-2 flex items-center gap-2">
            <h3 class="text-sm font-semibold text-ink-gray-8">{{ __("Service history") }}</h3>
            <Badge v-if="p.is_repeat_failure" theme="red" :label="__('Repeat failure')" />
          </div>
          <div v-if="!(p.service_history || []).length" class="py-3 text-sm text-ink-gray-5">
            {{ __("Nothing has been reported against this pump.") }}
          </div>
          <table v-else class="w-full text-sm">
            <tbody>
              <tr v-for="h in p.service_history" :key="h.name" class="border-b last:border-b-0">
                <td class="py-2 tabular-nums text-ink-gray-5">{{ String(h.reported_on).slice(0, 10) }}</td>
                <td class="py-2 text-ink-gray-8">{{ __(h.complaint_category || "—") }}</td>
                <td class="py-2 text-right">
                  <Badge :theme="h.status === 'Resolved' || h.status === 'Closed' ? 'green' : 'orange'"
                         :label="__(h.status)" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { Badge, Button, ErrorMessage, FormControl, createResource } from "frappe-ui";
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";
import ScanButton from "./ScanButton.vue";

const serial = ref("");
const notFound = ref("");
const p = ref<any>(null);

const snap = createResource({
  url: "kumar_service.api.get_pump_snapshot",
  onSuccess: (d: any) => {
    p.value = d;
    notFound.value = "";
  },
  onError: () => {
    p.value = null;
    notFound.value = __("No pump with that serial. Check the number on the nameplate.");
  },
});

function look() {
  const v = serial.value.trim();
  if (!v) return;
  notFound.value = "";
  snap.submit({ serial_no: v });
}

function onScanned(v: string) {
  serial.value = v;
  look();
}

// The verdict is the reason anyone opens this page, so it is the whole first
// card rather than a chip somewhere in a table.
const verdict = computed(() => {
  const d = p.value;
  if (!d) return {} as any;
  if (!d.is_registered) {
    return {
      headline: __("Not registered"),
      detail: __("No warranty has started. The dealer has to register the sale first."),
      card: "border-outline-gray-2 bg-surface-gray-1", strong: "text-ink-gray-9",
      muted: "text-ink-gray-6", bar: "bg-gray-400",
    };
  }
  const days = d.days_remaining;
  if (d.is_under_warranty) {
    const soon = days !== null && days <= (d.expiring_soon_days ?? 30);
    return {
      headline: soon ? __("Expiring soon") : __("In warranty"),
      detail: days !== null
        ? __("{0} days left. Nothing to pay on a visit.", [String(days)])
        : __("Nothing to pay on a visit."),
      card: soon ? "border-amber-200 bg-amber-50" : "border-green-200 bg-green-50",
      strong: soon ? "text-amber-800" : "text-green-800",
      muted: soon ? "text-amber-700" : "text-green-700",
      bar: soon ? "bg-amber-500" : "bg-green-500",
    };
  }
  return {
    headline: __("Out of warranty"),
    detail: days !== null && days < 0
      ? __("Expired {0} days ago. The visit is chargeable.", [String(Math.abs(days))])
      : __("The visit is chargeable."),
    card: "border-red-200 bg-red-50", strong: "text-red-800",
    muted: "text-red-700", bar: "bg-red-500",
  };
});

const used = computed(() => {
  const d = p.value;
  if (!d?.sale_date || !d?.warranty_expiry_date) return "0%";
  const start = new Date(d.sale_date).getTime();
  const end = new Date(d.warranty_expiry_date).getTime();
  const now = Date.now();
  if (end <= start) return "100%";
  return Math.min(100, Math.max(0, ((now - start) / (end - start)) * 100)).toFixed(1) + "%";
});

const whose = computed(() => {
  const d = p.value || {};
  return [
    { k: __("Customer"), v: d.end_customer_name },
    { k: __("Mobile"), v: d.end_customer_mobile, tel: true, mono: true },
    { k: __("Dealer"), v: d.dealer },
    { k: __("Sold on"), v: d.sale_date, mono: true },
    { k: __("Registration"), v: d.registration, mono: true },
  ];
});

const made = computed(() => {
  const d = p.value || {};
  return [
    { k: __("Built"), v: d.manufacturing_date },
    { k: __("QC"), v: d.qc_status },
    { k: __("Heat number"), v: d.heat_no },
    { k: __("Winding batch"), v: d.winding_batch },
    { k: __("Test certificate"), v: d.test_certificate },
  ];
});
</script>
