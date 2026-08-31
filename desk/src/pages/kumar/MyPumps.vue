<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ __("My Pumps") }}</div>
      </template>
    </LayoutHeader>
    <KumarNav />

    <div class="px-5 py-5">
      <div class="mb-4 flex flex-wrap items-center gap-3">
        <FormControl
          v-model="q"
          class="w-72"
          type="text"
          :placeholder="__('Customer, mobile, village or serial')"
        />
        <FormControl v-model="state" type="select" :options="stateOptions" class="w-48" />
        <div class="text-sm text-ink-gray-5">
          {{ __("{0} of {1}", [String(rows.length), String((pumps.data || []).length)]) }}
        </div>
      </div>

      <div v-if="pumps.loading" class="py-10 text-center text-ink-gray-5">
        {{ __("Loading...") }}
      </div>

      <div v-else-if="!rows.length" class="rounded border border-dashed py-10 text-center text-ink-gray-5">
        {{ __("No pump matches that search.") }}
      </div>

      <div v-else class="overflow-x-auto rounded border">
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
            <tr v-for="p in rows" :key="p.serial_no" class="border-t hover:bg-surface-gray-1">
              <td class="px-3 py-2 font-medium tabular-nums text-ink-gray-8">
                {{ p.serial_no }}
                <div class="text-xs font-normal text-ink-gray-5">{{ p.model }}</div>
              </td>
              <td class="px-3 py-2 text-ink-gray-7">{{ p.customer }}</td>
              <td class="px-3 py-2 text-ink-gray-7">{{ p.district }}</td>
              <td class="px-3 py-2 tabular-nums text-ink-gray-7">{{ p.sale_date }}</td>
              <td class="px-3 py-2">
                <Badge :theme="themeFor(p.state)" :label="__(p.state)" />
                <div class="mt-0.5 text-xs tabular-nums text-ink-gray-5">
                  {{ p.warranty_expiry_date }}
                </div>
              </td>
              <td class="px-3 py-2 text-right">
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
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { Badge, Button, FormControl, createResource } from "frappe-ui";
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";
import KumarNav from "./KumarNav.vue";

const router = useRouter();
const q = ref("");
const state = ref("");

const pumps = createResource({ url: "kumar_service.portal_api.my_pumps", auto: true });

const stateOptions = [
  { label: __("Any warranty state"), value: "" },
  { label: __("In Warranty"), value: "In Warranty" },
  { label: __("Expiring Soon"), value: "Expiring Soon" },
  { label: __("Expired"), value: "Expired" },
];

const rows = computed(() => {
  const term = q.value.trim().toLowerCase();
  return (pumps.data || []).filter((p: any) => {
    if (state.value && p.state !== state.value) return false;
    if (!term) return true;
    return [p.serial_no, p.model, p.customer, p.district].some((f: string) =>
      (f || "").toLowerCase().includes(term)
    );
  });
});

function themeFor(s: string) {
  if (s === "In Warranty") return "green";
  if (s === "Expiring Soon") return "orange";
  return "gray";
}

function complain(p: any) {
  router.push({ name: "KumarComplaint", query: { serial: p.serial_no } });
}
</script>
