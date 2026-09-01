<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ __("Visits") }}</div>
      </template>
      <template #right-header>
        <Button variant="ghost" :label="__('Refresh')" @click="board.reload()" />
      </template>
    </LayoutHeader>

    <div class="px-5 py-5">
      <div class="mb-5 grid gap-3 sm:grid-cols-3">
        <div class="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div class="text-xs font-medium text-amber-700">{{ __("Waiting for a visit") }}</div>
          <div class="mt-1 text-3xl font-semibold tabular-nums text-amber-800">
            {{ board.data?.needs_visit?.length ?? "-" }}
          </div>
        </div>
        <div class="rounded-xl border border-blue-200 bg-blue-50 p-4">
          <div class="text-xs font-medium text-blue-700">{{ __("Booked") }}</div>
          <div class="mt-1 text-3xl font-semibold tabular-nums text-blue-800">
            {{ board.data?.scheduled?.length ?? "-" }}
          </div>
        </div>
        <div class="rounded-xl border border-outline-gray-2 bg-surface-white p-4">
          <div class="text-xs font-medium text-ink-gray-5">{{ __("Technicians") }}</div>
          <div class="mt-1 text-3xl font-semibold tabular-nums text-ink-gray-9">
            {{ board.data?.technicians?.length ?? "-" }}
          </div>
        </div>
      </div>

      <!-- waiting ------------------------------------------------------ -->
      <div class="mb-2 flex items-center gap-3">
        <h2 class="text-sm font-semibold text-ink-gray-8">{{ __("Waiting for a visit") }}</h2>
        <FormControl v-model="q" class="w-64" type="text" :placeholder="__('Serial, customer, dealer')" />
      </div>

      <div v-if="board.loading" class="py-8 text-center text-ink-gray-5">{{ __("Loading...") }}</div>
      <div v-else-if="!waiting.length" class="rounded-lg border border-dashed py-8 text-center text-ink-gray-5">
        {{ __("Nothing is waiting on a visit.") }}
      </div>
      <div v-else class="overflow-x-auto rounded-lg border bg-surface-white">
        <table class="w-full text-sm">
          <thead class="bg-surface-gray-2 text-xs uppercase tracking-wide text-ink-gray-5">
            <tr>
              <th class="px-3 py-2 text-left font-medium">{{ __("Request") }}</th>
              <th class="px-3 py-2 text-left font-medium">{{ __("Customer") }}</th>
              <th class="px-3 py-2 text-left font-medium">{{ __("Where") }}</th>
              <th class="px-3 py-2 text-left font-medium">{{ __("Raised") }}</th>
              <th class="px-3 py-2 text-right font-medium"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in waiting" :key="r.name" class="border-t hover:bg-surface-gray-1">
              <td class="px-3 py-2">
                <div class="font-medium text-ink-gray-8">{{ r.custom_request_type || r.complaint_category }}</div>
                <div class="text-xs tabular-nums text-ink-gray-5">{{ r.serial_no }}</div>
              </td>
              <td class="px-3 py-2">
                <div class="text-ink-gray-7">{{ r.end_customer_name }}</div>
                <a v-if="r.end_customer_mobile" class="text-xs tabular-nums text-ink-blue-6 hover:underline"
                   :href="`tel:${r.end_customer_mobile}`">{{ r.end_customer_mobile }}</a>
              </td>
              <td class="px-3 py-2 text-ink-gray-7">
                <div>{{ r.where }}</div>
                <div class="text-xs text-ink-gray-5">{{ r.dealer }}</div>
              </td>
              <td class="px-3 py-2">
                <Badge :theme="r.overdue ? 'red' : 'gray'"
                       :label="r.overdue ? __('Past due') : String(r.status)" />
                <div class="mt-0.5 text-xs tabular-nums text-ink-gray-5">{{ shortDate(r.reported_on) }}</div>
              </td>
              <td class="whitespace-nowrap px-3 py-2 text-right">
                <Badge class="mr-2" :theme="r.is_under_warranty ? 'green' : 'orange'"
                       :label="r.is_under_warranty ? __('Free') : __('Chargeable')" />
                <Button variant="solid" theme="blue" :label="__('Schedule')" @click="openFor(r)" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- booked ------------------------------------------------------- -->
      <h2 class="mb-2 mt-8 text-sm font-semibold text-ink-gray-8">{{ __("Booked") }}</h2>
      <div v-if="!board.data?.scheduled?.length"
           class="rounded-lg border border-dashed py-8 text-center text-ink-gray-5">
        {{ __("No visits are booked.") }}
      </div>
      <div v-else class="overflow-x-auto rounded-lg border bg-surface-white">
        <table class="w-full text-sm">
          <thead class="bg-surface-gray-2 text-xs uppercase tracking-wide text-ink-gray-5">
            <tr>
              <th class="px-3 py-2 text-left font-medium">{{ __("Date") }}</th>
              <th class="px-3 py-2 text-left font-medium">{{ __("Technician") }}</th>
              <th class="px-3 py-2 text-left font-medium">{{ __("Pump") }}</th>
              <th class="px-3 py-2 text-left font-medium">{{ __("Customer") }}</th>
              <th class="px-3 py-2 text-left font-medium">{{ __("Type") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v in board.data.scheduled" :key="v.name" class="border-t hover:bg-surface-gray-1">
              <td class="px-3 py-2 font-medium tabular-nums text-ink-gray-8">{{ v.visit_date }}</td>
              <td class="px-3 py-2 text-ink-gray-7">{{ v.technician }}</td>
              <td class="px-3 py-2 tabular-nums text-ink-gray-7">{{ v.serial_no }}</td>
              <td class="px-3 py-2 text-ink-gray-7">{{ v.customer }}</td>
              <td class="px-3 py-2">
                <Badge :theme="v.is_chargeable ? 'orange' : 'green'"
                       :label="v.is_chargeable ? __('Chargeable') : __('Warranty')" />
                <span class="ml-2 text-xs text-ink-gray-5">{{ v.visit_type }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- schedule ------------------------------------------------------- -->
    <Dialog v-model="showing" :options="{ title: __('Schedule a visit') }">
      <template #body-content>
        <div v-if="target" class="mb-4 rounded-lg border bg-surface-gray-1 p-3 text-sm">
          <div class="font-medium text-ink-gray-8">{{ target.serial_no }}</div>
          <div class="text-ink-gray-6">
            {{ [target.end_customer_name, target.where].filter(Boolean).join(" · ") }}
          </div>
          <Badge class="mt-2" :theme="target.is_under_warranty ? 'green' : 'orange'"
                 :label="target.is_under_warranty
                   ? __('In warranty - nothing to pay')
                   : __('Out of warranty - chargeable')" />
        </div>

        <FormControl v-model="form.technician" type="select" :label="__('Technician')"
                     :options="technicianOptions" />
        <FormControl class="mt-3" v-model="form.visit_date" type="date" :label="__('Date')" />
        <FormControl class="mt-3" v-model="form.visit_type" type="select" :label="__('Visit type')"
                     :options="(board.data?.visit_types || []).map((t) => ({ label: __(t), value: t }))" />
        <FormControl class="mt-3" v-model="form.note" type="textarea" :rows="2"
                     :label="__('Anything to tell the dealer')"
                     :placeholder="__('e.g. Technician will call before leaving Tenali')" />

        <ErrorMessage v-if="book.error" class="mt-3" :message="book.error" />
      </template>
      <template #actions>
        <Button variant="solid" theme="blue" class="w-full" :loading="book.loading"
                :disabled="!form.technician || !form.visit_date"
                :label="__('Book it and tell the dealer')" @click="book.submit()" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { Badge, Button, Dialog, ErrorMessage, FormControl, createResource, toast } from "frappe-ui";
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";

const q = ref("");
const showing = ref(false);
const target = ref<any>(null);

const board = createResource({ url: "kumar_service.staff_api.visit_board", auto: true });

const waiting = computed(() => {
  const term = q.value.trim().toLowerCase();
  const rows = board.data?.needs_visit || [];
  if (!term) return rows;
  return rows.filter((r: any) =>
    [r.serial_no, r.end_customer_name, r.end_customer_mobile, r.dealer, r.where].some(
      (f: string) => (f || "").toLowerCase().includes(term)
    )
  );
});

const technicianOptions = computed(() => [
  { label: __("Choose a technician"), value: "" },
  ...(board.data?.technicians || []).map((t: any) => ({
    label: [t.technician_name || t.name, t.dealer].filter(Boolean).join(" · "),
    value: t.name,
  })),
]);

const form = reactive({ technician: "", visit_date: "", visit_type: "On-Site", note: "" });

function openFor(r: any) {
  target.value = r;
  form.technician = "";
  form.visit_date = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
  form.visit_type = "On-Site";
  form.note = "";
  showing.value = true;
}

function shortDate(v: string) {
  return v ? String(v).slice(0, 10) : "";
}

const book = createResource({
  url: "kumar_service.staff_api.schedule_visit",
  makeParams: () => ({
    service_request: target.value?.name,
    technician: form.technician,
    visit_date: form.visit_date,
    visit_type: form.visit_type,
    note: form.note,
  }),
  onSuccess: (d: any) => {
    showing.value = false;
    toast.success(d.message);
    board.reload();
  },
});
</script>
