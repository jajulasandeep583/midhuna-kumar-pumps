<template>
  <!-- Book a technician onto the job behind a ticket - from the ticket header,
       the KUMAR panel or a claims-desk card, through the same dialog. The
       dealer is told on their own thread either way. -->
  <Button :size="size" :variant="variant" :label="label" @click="open()">
    <template #prefix><LucideCalendarPlus class="size-4" /></template>
  </Button>

  <Dialog v-model="visiting" :options="{ title: __('Schedule a visit') }">
    <template #body-content>
      <div v-if="request" class="mb-3 rounded-lg border bg-surface-gray-1 p-3 text-sm text-ink-gray-7">
        {{ [request, serial].filter(Boolean).join(" · ") }}
      </div>
      <div v-else-if="claim" class="mb-3 rounded-lg border bg-surface-gray-1 p-3 text-sm text-ink-gray-7">
        {{ [claim, serial].filter(Boolean).join(" · ") }} ·
        {{ __("if the claim has no service request yet, booking opens one and links it") }}
      </div>
      <FormControl v-model="visit.technician" type="select" :label="__('Technician')" :options="technicianOptions" />
      <div class="mt-3 grid grid-cols-2 gap-3">
        <FormControl v-model="visit.visit_date" type="date" :label="__('Date')" />
        <FormControl v-model="visit.visit_type" type="select" :label="__('Type')" :options="VISIT_TYPES" />
      </div>
      <FormControl class="mt-3" v-model="visit.note" type="textarea" :rows="2"
        :label="__('Anything the dealer should know')" :placeholder="__('Optional')" />
      <ErrorMessage v-if="bookError" class="mt-3" :message="bookError" />
    </template>
    <template #actions>
      <Button class="w-full" variant="solid" :loading="bookRequest.loading || bookClaim.loading"
        :disabled="!visit.technician || !visit.visit_date"
        :label="__('Book it and tell the dealer')" @click="submit" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { Button, Dialog, ErrorMessage, FormControl, createResource, toast } from "frappe-ui";
import LucideCalendarPlus from "~icons/lucide/calendar-plus";
import { computed, reactive, ref } from "vue";

const props = withDefaults(
  defineProps<{
    request?: string | null;   // Service Request name - preferred when both exist
    claim?: string | null;     // Kumar Warranty Claim name
    serial?: string | null;
    technicians?: any[];       // [{ name, technician_name, dealer }]
    label?: string;
    variant?: string;
    size?: string;
  }>(),
  { request: null, claim: null, serial: null, technicians: () => [], label: "Schedule a visit", variant: "subtle", size: "sm" }
);
const emit = defineEmits<{ (e: "done", result: any): void }>();

const VISIT_TYPES = ["On-Site", "Workshop", "Telephonic"].map((v) => ({ label: __(v), value: v }));
const visiting = ref(false);
const visit = reactive({ technician: "", visit_date: "", visit_type: "On-Site", note: "" });

const technicianOptions = computed(() => [
  { label: __("Choose…"), value: "" },
  ...(props.technicians || []).map((t: any) => ({
    label: [t.technician_name || t.name, t.dealer].filter(Boolean).join(" · "),
    value: t.name,
  })),
]);

function open() {
  visit.technician = "";
  visit.visit_date = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
  visit.visit_type = "On-Site";
  visit.note = "";
  visiting.value = true;
}

const booked = {
  onSuccess: (d: any) => {
    visiting.value = false;
    toast.success(d?.message || __("Visit booked"));
    emit("done", d);
  },
};
const bookRequest = createResource({ url: "kumar_service.staff_api.schedule_visit", ...booked });
const bookClaim = createResource({ url: "kumar_service.staff_api.schedule_visit_for_claim", ...booked });
const bookError = computed(() => bookRequest.error || bookClaim.error);

function submit() {
  const p = { technician: visit.technician, visit_date: visit.visit_date, visit_type: visit.visit_type, note: visit.note };
  if (props.request) bookRequest.submit({ service_request: props.request, ...p });
  else if (props.claim) bookClaim.submit({ claim: props.claim, ...p });
}
</script>
