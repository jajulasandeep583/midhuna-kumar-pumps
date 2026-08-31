<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ __("Register a Sale") }}</div>
      </template>
    </LayoutHeader>

    <div class="mx-auto max-w-3xl px-5 py-6">
      <p class="mb-5 text-sm text-ink-gray-6">
        {{
          __(
            "Register the pump on the day you sell it - the warranty starts from the registration, and the customer's certificate is generated from it."
          )
        }}
      </p>

      <div class="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-gray-5">
        {{ __("1. Which pump?") }}
      </div>
      <div class="flex items-end gap-2">
        <FormControl
          class="flex-1"
          v-model="form.serial_no"
          type="text"
          :label="__('Serial number')"
          :placeholder="__('KP-... or scan the nameplate')"
          autocomplete="off"
          @change="check"
        />
        <ScanButton @scanned="onScanned" />
      </div>
      <div v-if="lookup.loading" class="mt-2 text-sm text-ink-gray-5">{{ __("Checking...") }}</div>
      <div v-else-if="found" class="mt-2 rounded border bg-surface-gray-1 p-3 text-sm">
        <span class="font-medium text-ink-gray-8">{{ found.pump_model }}</span>
        <span v-if="found.hp"> · {{ found.hp }} HP</span>
      </div>
      <ErrorMessage v-if="lookupError" class="mt-2" :message="lookupError" />

      <div class="mb-2 mt-6 text-xs font-semibold uppercase tracking-wider text-ink-gray-5">
        {{ __("2. Your bill to the customer") }}
      </div>
      <div class="grid gap-3 sm:grid-cols-2">
        <FormControl v-model="form.invoice_no" type="text" :label="__('Your invoice number')" />
        <FormControl v-model="form.sale_date" type="date" :label="__('Sale date')" />
      </div>

      <div class="mb-2 mt-6 text-xs font-semibold uppercase tracking-wider text-ink-gray-5">
        {{ __("3. Who bought it") }}
      </div>
      <div class="grid gap-3 sm:grid-cols-2">
        <FormControl v-model="form.end_customer_name" type="text" :label="__('Customer name')" />
        <FormControl v-model="form.end_customer_mobile" type="text" :label="__('Mobile')" />
      </div>

      <div class="mb-2 mt-6 text-xs font-semibold uppercase tracking-wider text-ink-gray-5">
        {{ __("4. Where it is installed") }}
      </div>
      <div class="grid gap-3 sm:grid-cols-2">
        <!-- an address is two or three lines, not a single-line box -->
        <FormControl
          class="sm:col-span-2"
          v-model="form.installation_address"
          type="textarea"
          :rows="3"
          :label="__('Village / address')"
          :placeholder="__('House number, street, village')"
        />
        <FormControl v-model="form.district" type="text" :label="__('District')" />
        <FormControl v-model="form.state" type="text" :label="__('State')" />
        <FormControl
          v-model="form.application_type"
          type="select"
          :label="__('Application')"
          :options="applicationOptions"
        />
      </div>

      <ErrorMessage v-if="submit.error" class="mt-3" :message="submit.error" />

      <Button
        class="mt-5 w-full"
        variant="solid"
        theme="blue"
        :loading="submit.loading"
        :disabled="!canSubmit"
        :label="__('Register & Get Warranty Certificate')"
        @click="submit.submit()"
      />

      <div v-if="done" class="mt-4 rounded border border-green-200 bg-green-50 p-3 text-sm">
        <div class="font-medium text-ink-gray-8">
          {{ __("Registered as {0}", [done.name]) }}
        </div>
        <a
          v-if="done.certificate_url"
          class="mt-2 inline-block text-sm font-medium text-ink-blue-3"
          :href="done.certificate_url"
          target="_blank"
          rel="noopener"
          >{{ __("Print Certificate") }}</a
        >
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { Button, ErrorMessage, FormControl, createResource } from "frappe-ui";
import { LayoutHeader } from "@/components";
import ScanButton from "./ScanButton.vue";
import { __ } from "@/translation";

const today = new Date().toISOString().slice(0, 10);
const form = reactive<any>({
  serial_no: "",
  invoice_no: "",
  sale_date: today,
  end_customer_name: "",
  end_customer_mobile: "",
  installation_address: "",
  district: "",
  state: "",
  application_type: "",
});
const found = ref<any>(null);
const lookupError = ref("");
const done = ref<any>(null);

const options = createResource({ url: "kumar_service.portal_api.portal_options", auto: true });
const applicationOptions = computed(() => [
  { label: __("Choose one"), value: "" },
  ...(options.data?.applications || []).map((a: string) => ({ label: __(a), value: a })),
]);

const lookup = createResource({
  url: "kumar_service.api.portal_serial_lookup",
  onSuccess: (d: any) => {
    found.value = d;
    lookupError.value = "";
  },
  onError: () => {
    found.value = null;
    lookupError.value = __("That serial is not available to register. Check the nameplate.");
  },
});

function onScanned(value: string) {
  form.serial_no = value;
  check();
}

function check() {
  found.value = null;
  lookupError.value = "";
  const sn = (form.serial_no || "").trim();
  if (sn.length > 4) lookup.submit({ serial_no: sn });
}

const canSubmit = computed(
  () =>
    !!form.serial_no &&
    !!form.end_customer_name &&
    !!form.end_customer_mobile &&
    !!form.sale_date
);

const submit = createResource({
  url: "kumar_service.api.register_pump",
  makeParams: () => ({ ...form }),
  onSuccess: (d: any) => {
    done.value = d;
    form.serial_no = "";
    form.invoice_no = "";
    form.end_customer_name = "";
    form.end_customer_mobile = "";
    form.installation_address = "";
    found.value = null;
  },
});
</script>
