<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ __("Pump Lookup") }}</div>
      </template>
    </LayoutHeader>

    <div class="mx-auto max-w-3xl px-5 py-6">
      <p class="mb-4 text-sm text-ink-gray-6">
        {{ __("Scan or type a serial to see if it is registered and how much warranty is left - your own sales come with the customer, anyone else's shows the warranty only.") }}
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
        <Button variant="solid" theme="blue" :loading="lookup.loading" :label="__('Look up')" @click="look()" />
        <ScanButton @scanned="onScanned" />
      </div>
      <ErrorMessage v-if="error" class="mt-2" :message="error" />

      <!-- not a pump we know -->
      <div v-if="p && !p.found" class="mt-6 rounded-xl border border-outline-gray-2 bg-surface-gray-1 p-5 text-sm text-ink-gray-7">
        {{ p.message }}
      </div>

      <div v-else-if="p" class="mt-6 space-y-4">
        <!-- the verdict, first -->
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

        <!-- your own sale: the whole record -->
        <div v-if="p.mine" class="rounded-xl border bg-surface-white p-4">
          <h3 class="mb-2 text-sm font-semibold text-ink-gray-8">{{ __("Your customer") }}</h3>
          <dl class="space-y-1.5 text-sm">
            <div v-for="r in whose" :key="r.k" class="flex justify-between gap-3">
              <dt class="text-ink-gray-5">{{ r.k }}</dt>
              <dd class="text-right text-ink-gray-8" :class="r.mono ? 'tabular-nums' : ''">
                <a v-if="r.tel && r.v" :href="`tel:${r.v}`" class="text-ink-blue-6 hover:underline">{{ r.v }}</a>
                <span v-else>{{ r.v || "—" }}</span>
              </dd>
            </div>
          </dl>
          <div class="mt-4 flex flex-wrap gap-2">
            <Button variant="solid" theme="blue" :label="__('Raise a Request')"
              @click="router.push({ name: 'KumarComplaintNew', query: { serial: p.serial_no } })" />
            <Button variant="subtle" :label="__('Warranty Claim')"
              @click="router.push({ name: 'KumarClaimNew', query: { serial: p.serial_no } })" />
          </div>
        </div>

        <!-- someone else's sale, or an unregistered pump: the honest note -->
        <div v-else-if="p.message" class="rounded-xl border border-outline-gray-2 bg-surface-gray-1 p-4 text-sm text-ink-gray-7">
          {{ p.message }}
        </div>

        <!-- what has gone wrong with it before (own pumps only) -->
        <div v-if="p.mine" class="rounded-xl border bg-surface-white p-4">
          <h3 class="mb-2 text-sm font-semibold text-ink-gray-8">{{ __("Service history") }}</h3>
          <div v-if="!(p.service_history || []).length" class="py-3 text-sm text-ink-gray-5">
            {{ __("Nothing has been reported against this pump.") }}
          </div>
          <table v-else class="w-full text-sm">
            <tbody>
              <tr v-for="h in p.service_history" :key="h.name" class="border-b last:border-b-0">
                <td class="py-2 tabular-nums text-ink-gray-5">{{ String(h.reported_on).slice(0, 10) }}</td>
                <td class="py-2 text-ink-gray-8">{{ __(h.custom_request_type || h.complaint_category || "—") }}</td>
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
import { computed, onMounted, ref } from "vue";
import { Badge, Button, ErrorMessage, FormControl, createResource } from "frappe-ui";
import { useRoute, useRouter } from "vue-router";
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";
import ScanButton from "./ScanButton.vue";

const router = useRouter();
const route = useRoute();
const serial = ref("");
const p = ref<any>(null);
const error = ref("");

const lookup = createResource({
  url: "kumar_service.portal_api.dealer_pump_lookup",
  onSuccess: (d: any) => {
    p.value = d;
    error.value = "";
  },
  onError: (e: any) => {
    p.value = null;
    error.value = e?.messages?.[0] || __("Could not look that serial up.");
  },
});

function look() {
  const v = serial.value.trim();
  if (!v) return;
  error.value = "";
  lookup.submit({ serial_no: v });
}

function onScanned(v: string) {
  serial.value = v;
  look();
}

// deep-linked from What I Sold or a request screen: land already looked up
onMounted(() => {
  const q = route.query.serial;
  if (typeof q === "string" && q) {
    serial.value = q;
    look();
  }
});

const verdict = computed(() => {
  const d = p.value;
  if (!d) return {} as any;
  if (!d.is_registered) {
    return {
      headline: __("Not registered"),
      detail: __("No warranty has started yet."),
      card: "border-outline-gray-2 bg-surface-gray-1", strong: "text-ink-gray-9",
      muted: "text-ink-gray-6", bar: "bg-gray-400",
    };
  }
  const days = d.days_remaining;
  if (d.in_warranty) {
    const soon = d.expiring_soon;
    return {
      headline: soon ? __("Expiring soon") : __("In warranty"),
      detail: days !== null && days !== undefined
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
    detail: days !== null && days !== undefined && days < 0
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
    { k: __("Where"), v: d.where },
    { k: __("Sold on"), v: d.sale_date, mono: true },
  ];
});
</script>
