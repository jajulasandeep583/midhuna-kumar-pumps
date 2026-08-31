<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ __("Warranty Claim") }}</div>
      </template>
    </LayoutHeader>

    <div class="mx-auto max-w-3xl px-5 py-6">
      <p class="mb-5 text-sm text-ink-gray-6">
        {{
          __(
            "Ask KUMAR to settle a failure under warranty. Name the parts and say what the technician found - a claim with evidence is settled faster than one without."
          )
        }}
      </p>

      <div class="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-gray-5">
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
        class="mt-1 max-h-56 overflow-y-auto rounded border bg-surface-white shadow-sm"
      >
        <li
          v-for="p in matches"
          :key="p.serial_no"
          class="cursor-pointer px-3 py-2 hover:bg-surface-gray-2"
          @click="take(p)"
        >
          <div class="text-sm font-medium text-ink-gray-8">{{ p.serial_no }}</div>
          <div class="text-xs text-ink-gray-5">
            {{ [p.model, p.customer].filter(Boolean).join(" · ") }}
          </div>
        </li>
      </ul>
      <div v-if="snapshot" class="mt-3 rounded border bg-surface-gray-1 p-3 text-sm">
        <div class="font-medium text-ink-gray-8">{{ snapshot.pump_model }}</div>
        <Badge
          class="mt-2"
          :theme="snapshot.in_warranty ? 'green' : 'orange'"
          :label="snapshot.in_warranty ? __('In warranty') : __('Out of warranty')"
        />
      </div>

      <div class="mb-2 mt-6 text-xs font-semibold uppercase tracking-wider text-ink-gray-5">
        {{ __("2. What failed") }}
      </div>
      <div class="grid gap-3 sm:grid-cols-2">
        <FormControl
          v-model="claimType"
          type="select"
          :label="__('Claim Type')"
          :options="claimTypeOptions"
        />
        <FormControl
          v-model="rootCause"
          type="select"
          :label="__('Root Cause')"
          :options="rootCauseOptions"
        />
      </div>

      <div class="mb-2 mt-6 text-xs font-semibold uppercase tracking-wider text-ink-gray-5">
        {{ __("3. What the technician found") }}
      </div>
      <FormControl
        v-model="report"
        type="textarea"
        :rows="4"
        :placeholder="__('What was dismantled, what was found, and why it is a manufacturing defect')"
      />

      <ErrorMessage v-if="submit.error" class="mt-3" :message="submit.error" />
      <Button
        class="mt-5 w-full"
        variant="solid"
        :loading="submit.loading"
        :disabled="!picked"
        :label="__('Lodge Claim with KUMAR')"
        @click="submit.submit()"
      />
      <div v-if="done" class="mt-4 rounded border border-green-200 bg-green-50 p-3 text-sm">
        {{ done.message || __("Claim lodged.") }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { Badge, Button, ErrorMessage, FormControl, createResource } from "frappe-ui";
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";

const query = ref("");
const picked = ref<any>(null);
const snapshot = ref<any>(null);
const claimType = ref("Part Replacement");
const rootCause = ref("");
const report = ref("");
const done = ref<any>(null);

const pumps = createResource({ url: "kumar_service.portal_api.my_pumps", auto: true });
const options = createResource({ url: "kumar_service.portal_api.portal_options", auto: true });

const claimTypeOptions = computed(() =>
  (options.data?.claim_types || []).map((c: string) => ({ label: __(c), value: c }))
);
const rootCauseOptions = computed(() => [
  { label: __("Not sure"), value: "" },
  ...(options.data?.root_causes || []).filter(Boolean).map((c: string) => ({ label: __(c), value: c })),
]);

const matches = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (q.length < 2) return [];
  return (pumps.data || [])
    .filter((p: any) =>
      [p.serial_no, p.model, p.customer].some((f: string) => (f || "").toLowerCase().includes(q))
    )
    .slice(0, 25);
});

function onType() {
  picked.value = null;
  snapshot.value = null;
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
  onSuccess: (d: any) => (snapshot.value = d),
});

const submit = createResource({
  url: "kumar_service.portal_api.raise_claim",
  makeParams: () => ({
    serial_no: picked.value?.serial_no,
    claim_type: claimType.value,
    root_cause: rootCause.value,
    technician_report: report.value,
  }),
  onSuccess: (d: any) => {
    done.value = d;
    picked.value = null;
    query.value = "";
    snapshot.value = null;
    report.value = "";
  },
});
</script>
