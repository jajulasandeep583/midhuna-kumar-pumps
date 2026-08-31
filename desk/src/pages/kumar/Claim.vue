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
      <!-- the app's own combobox rather than a hand-rolled list: it gives
           keyboard navigation, filtering and an empty state for free, and it is
           the control every other link field in the desk already uses -->
      <div class="flex items-center gap-2">
        <div class="flex-1">
          <Autocomplete
            v-model="selected"
            :options="pumpOptions"
            :placeholder="__('Type a serial, model or customer')"
            @update:model-value="onPick"
          />
        </div>
        <ScanButton @scanned="onScanned" />
      </div>
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

      <!-- 3. evidence ------------------------------------------------ -->
      <div class="mb-2 mt-6 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
        {{ __("4. Photos of the failed part") }}
      </div>
      <p class="mb-2 text-xs text-ink-gray-5">
        {{
          __(
            "A photograph of the failed part is the whole argument. A claim with evidence is settled faster than one without. Up to {0} MB each.",
            [String(MAX_MB)]
          )
        }}
      </p>

      <label
        class="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-outline-gray-3 bg-surface-gray-1 px-4 py-6 text-sm text-ink-gray-6 transition hover:border-outline-gray-4 hover:bg-surface-gray-2"
      >
        <LucidePaperclip class="size-4" />
        {{ __("Add photos or a video") }}
        <input
          type="file"
          class="hidden"
          multiple
          accept="image/*,video/*,application/pdf"
          @change="addFiles"
        />
      </label>

      <ul v-if="files.length" class="mt-3 space-y-2">
        <li
          v-for="(f, i) in files"
          :key="f.filename + i"
          class="flex items-center gap-3 rounded-lg border bg-surface-white p-2"
        >
          <img
            v-if="f.preview"
            :src="f.preview"
            alt=""
            class="size-12 shrink-0 rounded object-cover"
          />
          <span v-else class="grid size-12 shrink-0 place-items-center rounded bg-surface-gray-2">
            <LucideFile class="size-5 text-ink-gray-5" />
          </span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-sm text-ink-gray-8">{{ f.filename }}</span>
            <span class="text-xs text-ink-gray-5">{{ f.size }}</span>
          </span>
          <Button variant="ghost" :label="__('Remove')" @click="files.splice(i, 1)" />
        </li>
      </ul>
      <ErrorMessage v-if="fileError" class="mt-2" :message="fileError" />

      <ErrorMessage v-if="submit.error" class="mt-3" :message="submit.error" />
      <Button
        class="mt-5 w-full"
        variant="solid"
        theme="blue"
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
import { Autocomplete, LayoutHeader } from "@/components";
import ScanButton from "./ScanButton.vue";
import LucidePaperclip from "~icons/lucide/paperclip";
import LucideFile from "~icons/lucide/file";
import { __ } from "@/translation";

const selected = ref<any>(null);
const picked = ref<any>(null);
const snapshot = ref<any>(null);
const claimType = ref("Part Replacement");
const rootCause = ref("");
const report = ref("");
const done = ref<any>(null);

// Matches MAX_ATTACHMENT_MB in portal_api. Checked here as well so a dealer on
// a slow connection is told before uploading eight megabytes, not after.
const MAX_MB = 8;
const files = ref<any[]>([]);
const fileError = ref("");

function human(bytes: number) {
  return bytes > 1024 * 1024
    ? (bytes / 1024 / 1024).toFixed(1) + " MB"
    : Math.max(1, Math.round(bytes / 1024)) + " KB";
}


const pumps = createResource({ url: "kumar_service.portal_api.my_pumps", auto: true });
const options = createResource({ url: "kumar_service.portal_api.portal_options", auto: true });

const claimTypeOptions = computed(() =>
  (options.data?.claim_types?.length
    ? options.data.claim_types
    : ["Part Replacement", "Full Replacement", "Repair Reimbursement"]
  ).map((c: string) => ({ label: __(c), value: c }))
);
const rootCauseOptions = computed(() => [
  { label: __("Not sure"), value: "" },
  ...(options.data?.root_causes || []).filter(Boolean).map((c: string) => ({ label: __(c), value: c })),
]);



// label carries everything a dealer might search on, because Autocomplete
// filters on the label - serial alone would not find "Gopal Rao"
const pumpOptions = computed(() =>
  (pumps.data || []).map((p: any) => ({
    label: [p.serial_no, p.model, p.customer, p.district].filter(Boolean).join(" · "),
    value: p.serial_no,
  }))
);

function onScanned(serial: string) {
  const hit = (pumps.data || []).find((p: any) => p.serial_no === serial);
  if (hit) take(hit);
}

function onPick(opt: any) {
  const serial = opt?.value || opt;
  const hit = (pumps.data || []).find((p: any) => p.serial_no === serial);
  if (hit) take(hit);
}

function take(p: any) {
  picked.value = p;
  selected.value = { label: p.serial_no, value: p.serial_no };
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
    attachments: files.value.map((f) => ({ filename: f.filename, content: f.content })),
  }),
  onSuccess: (d: any) => {
    done.value = d;
    picked.value = null;
    selected.value = null;
    snapshot.value = null;
    report.value = "";
    files.value.forEach((f) => f.preview && URL.revokeObjectURL(f.preview));
    files.value = [];
  },
});
</script>
