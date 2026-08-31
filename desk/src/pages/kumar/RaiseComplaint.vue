<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">
          {{ __("Raise a Complaint") }}
        </div>
      </template>
    </LayoutHeader>

    <div class="mx-auto max-w-3xl px-5 py-6">
      <p class="mb-5 text-sm text-ink-gray-6">
        {{
          __(
            "Log what the customer is reporting. We answer immediately whether the visit is free, and the response clock starts the moment you submit."
          )
        }}
      </p>

      <!-- 1. the pump ------------------------------------------------ -->
      <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
        {{ __("1. Which pump?") }}
      </div>
      <FormControl
        v-model="query"
        type="text"
        :placeholder="__('Type a serial, model or customer - or scan')"
        autocomplete="off"
        @update:model-value="onType"
      />

      <ul
        v-if="matches.length && !picked"
        class="mt-1 max-h-64 overflow-y-auto rounded border bg-surface-white shadow-sm"
      >
        <li
          v-for="p in matches"
          :key="p.serial_no"
          class="cursor-pointer px-3 py-2 hover:bg-surface-gray-2"
          @click="take(p)"
        >
          <div class="text-sm font-medium text-ink-gray-8">{{ p.serial_no }}</div>
          <div class="text-xs text-ink-gray-5">
            {{ [p.model, p.customer, p.district].filter(Boolean).join(" · ") }}
          </div>
        </li>
      </ul>

      <div v-if="snapshot" class="mt-3 rounded border bg-surface-gray-1 p-3 text-sm">
        <div class="font-medium text-ink-gray-8">
          {{ snapshot.pump_model }}
          <span v-if="snapshot.hp"> · {{ snapshot.hp }} HP</span>
        </div>
        <div v-if="snapshot.end_customer_name" class="text-ink-gray-6">
          {{ snapshot.end_customer_name }}
          <span v-if="snapshot.end_customer_mobile">· {{ snapshot.end_customer_mobile }}</span>
        </div>
        <Badge
          class="mt-2"
          :theme="snapshot.in_warranty ? 'green' : 'orange'"
          :label="
            snapshot.in_warranty
              ? __('In warranty - not chargeable')
              : __('Out of warranty - chargeable')
          "
        />
      </div>
      <ErrorMessage v-if="lookupError" class="mt-2" :message="lookupError" />

      <!-- 2. what is wrong -------------------------------------------- -->
      <div class="mb-2 mt-6 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
        {{ __("2. What is happening") }}
      </div>
      <div class="grid gap-3 sm:grid-cols-2">
        <FormControl
          v-model="category"
          type="select"
          :label="__('What is the problem')"
          :options="categoryOptions"
        />
        <FormControl
          v-model="priority"
          type="select"
          :label="__('Priority')"
          :options="priorityOptions"
        />
      </div>
      <FormControl
        v-model="description"
        class="mt-3"
        type="textarea"
        :rows="4"
        :label="__(`Describe the problem in the customer's own words`)"
        :placeholder="__('e.g. No water since two days, motor runs but nothing comes up')"
      />

      <ErrorMessage v-if="submit.error" class="mt-3" :message="submit.error" />

      <Button
        class="mt-5 w-full"
        variant="solid"
        :loading="submit.loading"
        :disabled="!canSubmit"
        :label="__('Send to KUMAR')"
        @click="send"
      />

      <div v-if="done" class="mt-4 rounded border border-green-200 bg-green-50 p-3 text-sm">
        <div class="font-medium text-ink-gray-8">{{ done.message }}</div>
        <Button
          class="mt-2"
          :label="__('See my tickets')"
          @click="router.push({ name: 'TicketsCustomer' })"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Badge, Button, ErrorMessage, FormControl, createResource } from "frappe-ui";
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";

const router = useRouter();
const route = useRoute();

const query = ref("");
const picked = ref<any>(null);
const snapshot = ref<any>(null);
const lookupError = ref("");
const category = ref("");
const priority = ref("Medium");
const description = ref("");
const done = ref<any>(null);

// the dealer's own pumps, searched in the browser - the same list the portal uses
const pumps = createResource({
  url: "kumar_service.portal_api.my_pumps",
  auto: true,
  onSuccess: () => preselect(),
});

// Arriving from a row in What I Sold: fill the pump in rather than making the
// dealer pick the one they just clicked. The list has to have loaded first,
// hence doing it on the resource rather than on mount.
function preselect() {
  const wanted = String(route.query.serial || "");
  if (!wanted || picked.value) return;
  const hit = (pumps.data || []).find((p: any) => p.serial_no === wanted);
  if (hit) take(hit);
}

const options = createResource({
  url: "kumar_service.portal_api.portal_options",
  auto: true,
});

const categoryOptions = computed(() => [
  { label: __("Choose one"), value: "" },
  ...(options.data?.complaint_categories || []).map((c: string) => ({ label: __(c), value: c })),
]);

const priorityOptions = computed(() =>
  (options.data?.priorities || ["Low", "Medium", "High", "Critical"]).map((p: string) => ({
    label: __(p),
    value: p,
  }))
);

const matches = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q || q.length < 2) return [];
  const rows = pumps.data || [];
  return rows
    .filter((p: any) =>
      [p.serial_no, p.model, p.customer, p.district]
        .some((f: string) => (f || "").toLowerCase().includes(q))
    )
    .slice(0, 25);
});

function onType() {
  picked.value = null;
  snapshot.value = null;
  lookupError.value = "";
  // a barcode scanner types an exact serial: take it without a click
  const exact = (pumps.data || []).find(
    (p: any) => p.serial_no.toLowerCase() === query.value.trim().toLowerCase()
  );
  if (exact) take(exact);
}

function take(p: any) {
  picked.value = p;
  query.value = p.serial_no;
  lookup.submit({ serial_no: p.serial_no });
}

const lookup = createResource({
  url: "kumar_service.portal_api.pump_snapshot",
  onSuccess: (d: any) => {
    snapshot.value = d;
    lookupError.value = "";
  },
  onError: () => {
    snapshot.value = null;
    lookupError.value = __("We have no record of that serial. Check the number on the nameplate.");
  },
});

const canSubmit = computed(
  () => !!picked.value && !!category.value && description.value.trim().length > 0
);

const submit = createResource({
  url: "kumar_service.portal_api.raise_complaint",
  makeParams: () => ({
    serial_no: picked.value?.serial_no,
    complaint_category: category.value,
    complaint_description: description.value,
    priority: priority.value,
  }),
  onSuccess: (d: any) => {
    done.value = d;
    query.value = "";
    picked.value = null;
    snapshot.value = null;
    category.value = "";
    description.value = "";
  },
});

function send() {
  done.value = null;
  submit.submit();
}
</script>
