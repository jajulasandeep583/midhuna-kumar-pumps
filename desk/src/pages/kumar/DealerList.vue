<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ title }}</div>
      </template>
      <template #right-header>
        <Button variant="solid" theme="blue" :label="addLabel" @click="router.push({ name: newRoute })">
          <template #prefix><LucidePlus class="size-4" /></template>
        </Button>
      </template>
    </LayoutHeader>

    <div class="px-5 py-5">
      <div class="mb-4 flex flex-wrap items-center gap-3">
        <FormControl v-model="q" class="w-72" type="text" :placeholder="searchHint" />
        <FormControl v-model="state" type="select" class="w-52" :options="stateOptions" />
        <span class="text-sm text-ink-gray-5">
          {{ __("{0} of {1}", [String(rows.length), String(all.length)]) }}
          <span v-if="openCount" class="ml-1 text-ink-gray-7">
            · {{ __("{0} still open", [String(openCount)]) }}
          </span>
        </span>
      </div>

      <div v-if="list.loading && !list.data" class="py-12 text-center text-ink-gray-5">
        {{ __("Loading...") }}
      </div>

      <div v-else-if="!all.length" class="rounded-xl border border-dashed py-14 text-center">
        <p class="text-ink-gray-6">{{ emptyLine }}</p>
        <Button class="mt-3" variant="solid" theme="blue" :label="addLabel"
                @click="router.push({ name: newRoute })" />
      </div>

      <div v-else-if="!rows.length" class="rounded-xl border border-dashed py-12 text-center text-ink-gray-5">
        {{ __("Nothing matches that search.") }}
      </div>

      <div v-else class="overflow-x-auto rounded-lg border bg-surface-white">
        <table class="w-full text-sm">
          <thead class="bg-surface-gray-2 text-xs uppercase tracking-wide text-ink-gray-5">
            <tr>
              <th class="px-3 py-2 text-left font-medium">{{ __("What") }}</th>
              <th class="px-3 py-2 text-left font-medium">{{ __("Pump") }}</th>
              <th class="px-3 py-2 text-left font-medium">{{ __("Raised") }}</th>
              <th class="px-3 py-2 text-left font-medium">{{ __("Status") }}</th>
              <th class="px-3 py-2 text-right font-medium"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.name" class="border-t hover:bg-surface-gray-1">
              <td class="px-3 py-2">
                <div class="font-medium text-ink-gray-8">{{ r.headline || r.kind_label }}</div>
                <div class="text-xs tabular-nums text-ink-gray-5">{{ r.name }}</div>
              </td>
              <td class="px-3 py-2">
                <div class="tabular-nums text-ink-gray-7">{{ r.serial_no }}</div>
                <div class="text-xs text-ink-gray-5">{{ r.pump_model }}</div>
              </td>
              <td class="px-3 py-2 tabular-nums text-ink-gray-7">{{ r.on }}</td>
              <td class="px-3 py-2">
                <Badge :theme="tone(r)" :label="__(r.status)" />
                <div v-if="r.amount" class="mt-0.5 text-xs tabular-nums text-ink-gray-5">
                  {{ money(r.amount) }}
                </div>
              </td>
              <td class="whitespace-nowrap px-3 py-2 text-right">
                <!-- KUMAR answering is the thing a dealer is waiting for, so it
                     is on the row rather than inside the ticket -->
                <Badge v-if="r.kumar_replied" theme="green" :label="__('KUMAR replied')" />
                <Button class="ml-2" variant="subtle" :label="__('Open')"
                        @click="router.push({ name: 'TicketCustomer', params: { ticketId: r.name } })" />
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
import LucidePlus from "~icons/lucide/plus";

const props = defineProps<{
  kind: "claim" | "complaint";
  title: string;
  addLabel: string;
  newRoute: string;
  emptyLine: string;
  searchHint: string;
}>();

const router = useRouter();
const q = ref("");
const state = ref("");

const list = createResource({
  url: "kumar_service.portal_api.my_tickets",
  auto: true,
  makeParams: () => ({ kind: props.kind }),
});

// my_tickets returns {tickets, open, total, statuses} rather than a bare list
const all = computed(() => list.data?.tickets || []);
const openCount = computed(() => list.data?.open ?? 0);

// the server already sends only the statuses actually present, so the filter
// never offers an option that would return nothing
const stateOptions = computed(() => [
  { label: __("Any status"), value: "" },
  ...(list.data?.statuses || []).map((s: any) => ({ label: __(s), value: s })),
]);

const rows = computed(() => {
  const term = q.value.trim().toLowerCase();
  return all.value.filter((r: any) => {
    if (state.value && r.status !== state.value) return false;
    if (!term) return true;
    return [r.name, r.serial_no, r.pump_model, r.headline].some((f: string) =>
      (f || "").toLowerCase().includes(term)
    );
  });
});

function money(v: number) {
  return "₹" + Math.round(v || 0).toLocaleString("en-IN");
}

function tone(r: any) {
  if (r.closed) return r.approved === false ? "gray" : "green";
  if (r.tone === "warning") return "orange";
  return "blue";
}
</script>
