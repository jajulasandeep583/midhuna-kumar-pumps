<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">
          {{ __("Raise a Request") }}
        </div>
      </template>
    </LayoutHeader>

    <div class="mx-auto max-w-3xl px-5 py-6">
      <p class="mb-5 text-sm text-ink-gray-6">
        {{
          __(
            "Tell KUMAR what you need - a fault to fix, an installation, a paid visit or a part. We answer immediately whether the visit is free, and the response clock starts the moment you submit."
          )
        }}
      </p>

      <!-- 1. the pump ------------------------------------------------ -->
      <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
        {{ __("1. What do you need?") }}
      </div>
      <!-- One form, not two. Every one of these files the same Service Request;
           what changes is what the desk is being asked to do about it. -->
      <div class="mb-6 flex flex-wrap gap-2">
        <button
          v-for="t in requestTypes"
          :key="t.value"
          class="rounded-lg border px-3 py-2 text-sm transition"
          :class="
            requestType === t.value
              ? 'border-blue-300 bg-blue-50 font-medium text-blue-800'
              : 'border-outline-gray-2 bg-surface-white text-ink-gray-7 hover:bg-surface-gray-2'
          "
          @click="requestType = t.value"
        >
          {{ t.label }}
        </button>
      </div>

      <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
        {{ __("2. Which pump?") }}
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
        {{ isComplaint ? __("3. What is wrong") : __("3. What do you need done") }}
      </div>
      <div class="grid gap-3 sm:grid-cols-2">
        <FormControl
          v-if="isComplaint"
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
        :label="isComplaint
          ? __(`Describe the problem in the customer's own words`)
          : __('What do you need, and by when')"
        :placeholder="isComplaint
          ? __('e.g. No water since two days, motor runs but nothing comes up')
          : __('e.g. New 5 HP set to be installed at the borewell on Thursday')"
      />

      <!-- 3. evidence ------------------------------------------------ -->
      <div class="mb-2 mt-6 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
        {{ __("4. Photos or a video") }}
      </div>
      <p class="mb-2 text-xs text-ink-gray-5">
        {{
          __(
            "A photo of the nameplate, the leak or the burnt winding decides whether we send a technician. Up to {0} MB each.",
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
import { Autocomplete, LayoutHeader } from "@/components";
import ScanButton from "./ScanButton.vue";
import LucidePaperclip from "~icons/lucide/paperclip";
import LucideFile from "~icons/lucide/file";
import { __ } from "@/translation";

const router = useRouter();
const route = useRoute();

const selected = ref<any>(null);
const picked = ref<any>(null);
const snapshot = ref<any>(null);
const lookupError = ref("");
const category = ref("");
const requestType = ref("Complaint");
const isComplaint = computed(() => requestType.value === "Complaint");
const priority = ref("Medium");
const description = ref("");
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

async function addFiles(e: Event) {
  fileError.value = "";
  const picked = Array.from((e.target as HTMLInputElement).files || []);
  for (const file of picked) {
    if (file.size > MAX_MB * 1024 * 1024) {
      fileError.value = __("{0} is too large. The limit is {1} MB.", [file.name, String(MAX_MB)]);
      continue;
    }
    const content = await new Promise<string>((resolve) => {
      const reader = new FileReader();
      // the API takes base64, so strip the data: prefix the reader adds
      reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
      reader.readAsDataURL(file);
    });
    files.value.push({
      filename: file.name,
      content,
      size: human(file.size),
      preview: file.type.startsWith("image/") ? URL.createObjectURL(file) : "",
    });
  }
  (e.target as HTMLInputElement).value = "";
}

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

// A fallback, not decoration: if the options call is slow or fails the dealer
// still gets a usable form instead of a dropdown with one empty entry.
const FALLBACK_CATEGORIES = [
  "No Discharge", "Low Discharge", "Motor Burnt", "Noise & Vibration", "Leakage",
  "Tripping", "Seal Failure", "Bearing Failure", "Impeller Damage", "Cable Fault",
  "Installation Issue", "Other",
];

const categoryOptions = computed(() => [
  { label: __("Choose one"), value: "" },
  ...(options.data?.complaint_categories?.length
    ? options.data.complaint_categories
    : FALLBACK_CATEGORIES
  ).map((c: string) => ({ label: __(c), value: c })),
]);

const requestTypes = computed(() =>
  (options.data?.request_types?.length
    ? options.data.request_types
    : ["Complaint", "Installation", "Paid Service", "Spare Part", "Enquiry"]
  ).map((t: string) => ({ label: __(t), value: t }))
);

const priorityOptions = computed(() =>
  (options.data?.priorities || ["Low", "Medium", "High", "Critical"]).map((p: string) => ({
    label: __(p),
    value: p,
  }))
);



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
  () =>
    !!picked.value &&
    (!isComplaint.value || !!category.value) &&
    description.value.trim().length > 0
);

const submit = createResource({
  url: "kumar_service.portal_api.raise_complaint",
  makeParams: () => ({
    serial_no: picked.value?.serial_no,
    complaint_description: description.value,
    priority: priority.value,
    request_type: requestType.value,
    // the desk needs a category on a fault; on anything else it is noise
    complaint_category: isComplaint.value ? category.value : "Other",
    attachments: files.value.map((f) => ({ filename: f.filename, content: f.content })),
  }),
  onSuccess: (d: any) => {
    done.value = d;
    selected.value = null;
    picked.value = null;
    snapshot.value = null;
    category.value = "";
    description.value = "";
    files.value.forEach((f) => f.preview && URL.revokeObjectURL(f.preview));
    files.value = [];
  },
});

function send() {
  done.value = null;
  submit.submit();
}
</script>
