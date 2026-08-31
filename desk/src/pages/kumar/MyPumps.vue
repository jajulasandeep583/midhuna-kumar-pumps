<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ __("What I Sold") }}</div>
      </template>
      <template #right-header>
        <Button variant="solid" :label="__('Register a Sale')" @click="router.push({ name: 'KumarRegister' })" />
      </template>
    </LayoutHeader>

    <div class="px-5 py-5">
      <p class="mb-4 text-sm text-ink-gray-6">
        {{
          __(
            "Search by customer name, mobile, village or serial number. A pump whose warranty is running out is a customer worth ringing."
          )
        }}
      </p>

      <!-- Scan first: a scanner types fast and sends Enter, and the dealer
           holding the pump has the barcode, not the customer's name. -->
      <div class="mb-3 flex flex-wrap items-end gap-2 rounded-lg border bg-surface-gray-1 p-3">
        <div class="w-full sm:w-80">
          <label class="mb-1 block text-xs font-medium text-ink-gray-5">
            {{ __("Scan a barcode") }}
          </label>
          <FormControl
            ref="scanBox"
            v-model="scan"
            type="text"
            :placeholder="__('Scan or type a serial, then Enter')"
            autocomplete="off"
            @keydown.enter.prevent="onScan"
          />
        </div>
        <Button :label="__('Find')" @click="onScan" />
        <div v-if="scanMsg" class="pb-2 text-xs" :class="scanOk ? 'text-ink-green-3' : 'text-ink-red-3'">
          {{ scanMsg }}
        </div>
      </div>

      <!-- the same five filters the portal has, plus the date range -->
      <div class="mb-4 grid gap-3 rounded-lg border bg-surface-gray-1 p-3 sm:grid-cols-2 lg:grid-cols-4">
        <FormControl v-model="f.q" type="text" :label="__('Search')"
          :placeholder="__('Customer, mobile, village or serial')" />
        <FormControl v-model="f.state" type="select" :label="__('Warranty')" :options="stateOptions" />
        <FormControl v-model="f.category" type="select" :label="__('Product Family')" :options="categoryOptions" />
        <FormControl v-model="f.model" type="select" :label="__('Model')" :options="modelOptions" />
        <FormControl v-model="f.district" type="select" :label="__('District')" :options="districtOptions" />
        <FormControl v-model="f.from" type="date" :label="__('Sold From')" />
        <FormControl v-model="f.to" type="date" :label="__('Sold To')" />
        <div class="flex items-end">
          <Button class="w-full" :label="__('Clear filters')" @click="clear" />
        </div>
      </div>

      <div class="mb-2 text-sm text-ink-gray-5">
        {{
          rows.length === all.length
            ? __("Showing all {0}", [String(all.length)])
            : __("{0} of {1}", [String(rows.length), String(all.length)])
        }}
      </div>

      <div v-if="pumps.loading" class="py-10 text-center text-ink-gray-5">{{ __("Loading...") }}</div>
      <div v-else-if="!rows.length" class="rounded-lg border border-dashed py-10 text-center text-ink-gray-5">
        {{ __("No pump matches that search.") }}
      </div>

      <div v-else class="overflow-x-auto rounded-lg border bg-surface-white">
        <table class="w-full text-sm">
          <thead class="bg-surface-gray-2 text-xs uppercase tracking-wide text-ink-gray-5">
            <tr>
              <th class="px-3 py-2 text-left font-medium">{{ __("Serial") }}</th>
              <th class="px-3 py-2 text-left font-medium">{{ __("Customer") }}</th>
              <th class="px-3 py-2 text-left font-medium">{{ __("Where") }}</th>
              <th class="px-3 py-2 text-left font-medium">{{ __("Sold") }}</th>
              <th class="px-3 py-2 text-left font-medium">{{ __("Warranty") }}</th>
              <th class="px-3 py-2 text-right font-medium"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="p in rows"
              :key="p.serial_no"
              class="border-t hover:bg-surface-gray-1"
              :class="p.serial_no === highlighted ? 'bg-surface-amber-1' : ''"
            >
              <td class="px-3 py-2">
                <div class="font-medium tabular-nums text-ink-gray-8">{{ p.serial_no }}</div>
                <div class="text-xs text-ink-gray-5">{{ p.model }}</div>
              </td>
              <td class="px-3 py-2">
                <div class="text-ink-gray-7">{{ p.customer }}</div>
                <a v-if="p.mobile" class="text-xs tabular-nums text-ink-blue-3" :href="`tel:${p.mobile}`">
                  {{ p.mobile }}
                </a>
              </td>
              <td class="px-3 py-2 text-ink-gray-7">
                <div>{{ p.where }}</div>
                <div class="text-xs text-ink-gray-5">{{ p.district }}</div>
              </td>
              <td class="px-3 py-2 tabular-nums text-ink-gray-7">{{ p.sale_date }}</td>
              <td class="px-3 py-2">
                <Badge :theme="themeFor(p.state)" :label="__(p.state)" />
                <div class="mt-0.5 text-xs tabular-nums text-ink-gray-5">
                  {{ p.warranty_expiry_date }}
                  <span v-if="p.days_left !== null && p.days_left >= 0">
                    · {{ __("{0} days left", [String(p.days_left)]) }}
                  </span>
                </div>
              </td>
              <td class="whitespace-nowrap px-3 py-2 text-right">
                <Button :label="__('Complaint')" @click="complain(p)" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { Badge, Button, FormControl, createResource } from "frappe-ui";
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";

const router = useRouter();
const pumps = createResource({ url: "kumar_service.portal_api.my_pumps", auto: true });
const all = computed(() => pumps.data || []);

const f = reactive({ q: "", state: "", category: "", model: "", district: "", from: "", to: "" });
const scan = ref("");
const scanMsg = ref("");
const scanOk = ref(false);
const highlighted = ref("");

function uniq(key: string) {
  return [...new Set(all.value.map((p: any) => p[key]).filter(Boolean))].sort();
}
const opts = (label: string, key: string) =>
  computed(() => [
    { label, value: "" },
    ...uniq(key).map((v: any) => ({ label: String(v), value: v })),
  ]);

const categoryOptions = opts(__("Any family"), "category");
const modelOptions = opts(__("Any model"), "model");
const districtOptions = opts(__("Any district"), "district");
const stateOptions = [
  { label: __("Any"), value: "" },
  { label: __("In Warranty"), value: "In Warranty" },
  { label: __("Expiring Soon"), value: "Expiring Soon" },
  { label: __("Expired"), value: "Expired" },
];

const rows = computed(() => {
  const term = f.q.trim().toLowerCase();
  return all.value.filter((p: any) => {
    if (f.state && p.state !== f.state) return false;
    if (f.category && p.category !== f.category) return false;
    if (f.model && p.model !== f.model) return false;
    if (f.district && p.district !== f.district) return false;
    if (f.from && (!p.sale_date || p.sale_date < f.from)) return false;
    if (f.to && (!p.sale_date || p.sale_date > f.to)) return false;
    if (!term) return true;
    return [p.serial_no, p.model, p.customer, p.mobile, p.where, p.district].some((x: string) =>
      (x || "").toLowerCase().includes(term)
    );
  });
});

function clear() {
  Object.assign(f, { q: "", state: "", category: "", model: "", district: "", from: "", to: "" });
  highlighted.value = "";
}

function onScan() {
  const v = scan.value.trim();
  if (!v) return;
  const hit = all.value.find(
    (p: any) => (p.serial_no || "").toLowerCase() === v.toLowerCase()
  );
  if (hit) {
    // clear the filters so the scanned pump cannot be hidden by one of them
    clear();
    highlighted.value = hit.serial_no;
    f.q = hit.serial_no;
    scanOk.value = true;
    scanMsg.value = __("Found {0}", [hit.customer || hit.serial_no]);
  } else {
    scanOk.value = false;
    scanMsg.value = __("That serial is not in your list.");
  }
  scan.value = "";
  nextTick(() => window.scrollTo({ top: 0 }));
}

function themeFor(s: string) {
  if (s === "In Warranty") return "green";
  if (s === "Expiring Soon") return "orange";
  return "gray";
}

function complain(p: any) {
  router.push({ name: "KumarComplaint", query: { serial: p.serial_no } });
}
</script>
