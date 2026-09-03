<template>
  <!-- Everything KUMAR knows about the job behind this ticket, next to the
       conversation. An agent on the phone should never have to leave the
       ticket to find the pump, the warranty, the claim or the visits. -->
  <Section :label="__('KUMAR Pumps')" v-model:opened="opened">
    <div class="space-y-3 pb-3 pt-0.5 text-sm">
      <div v-if="ctx.loading && !ctx.data" class="text-ink-gray-5">{{ __("Loading…") }}</div>
      <ErrorMessage v-else-if="ctx.error" :message="ctx.error" />
      <template v-else-if="ctx.data">
        <!-- the pump -->
        <div v-if="ctx.data.serial_no" class="rounded-lg border bg-surface-gray-1 p-3">
          <div class="flex items-center justify-between gap-2">
            <button
              class="truncate font-semibold tabular-nums text-ink-gray-9 hover:underline"
              :title="__('Open in Pump Lookup')"
              @click="openLookup"
            >
              {{ ctx.data.serial_no }}
            </button>
            <Badge :label="warranty.label" :theme="warranty.theme" variant="subtle" />
          </div>
          <div class="mt-0.5 text-ink-gray-6">
            {{ request?.pump_model || "" }}<span v-if="request?.pump_model && request?.dealer"> · </span>{{ request?.dealer || "" }}
          </div>
          <div v-if="ctx.data.site?.installation_address || ctx.data.site?.district" class="mt-1 text-xs text-ink-gray-5">
            {{ [ctx.data.site?.installation_address, ctx.data.site?.district].filter(Boolean).join(", ") }}
          </div>
          <div v-if="ctx.data.site?.warranty_expiry_date" class="mt-0.5 text-xs text-ink-gray-5">
            {{ __("Warranty till {0}", [fmt(ctx.data.site.warranty_expiry_date)]) }}
          </div>
        </div>

        <!-- the request -->
        <div v-if="request" class="space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-medium text-ink-gray-8">{{ request.name }}</span>
            <Badge :label="request.status" :theme="statusTheme(request.status)" variant="subtle" />
          </div>
          <div class="text-ink-gray-6">
            {{ [request.custom_request_type, request.complaint_category].filter(Boolean).join(" · ") }}
            <span v-if="request.priority"> · {{ request.priority }}</span>
          </div>
          <div v-if="request.end_customer_name" class="text-ink-gray-6">
            {{ __("For") }} {{ request.end_customer_name }}<span v-if="request.end_customer_mobile"> · {{ request.end_customer_mobile }}</span>
          </div>
          <div v-if="request.assigned_technician" class="text-ink-gray-6">
            {{ __("Technician") }}: {{ request.assigned_technician }}
          </div>
          <!-- the two SLA clocks, in words -->
          <div class="flex flex-wrap gap-x-3 gap-y-0.5 text-xs">
            <span :class="request.first_response_on ? 'text-green-700' : overdue(request.response_due_on) ? 'text-red-600' : 'text-ink-gray-5'">
              {{ request.first_response_on
                ? __("Replied {0}", [fmt(request.first_response_on)])
                : request.response_due_on ? __("Reply due {0}", [fmt(request.response_due_on)]) : "" }}
            </span>
            <span :class="request.resolved_on ? 'text-green-700' : overdue(request.resolution_due_on) ? 'text-red-600' : 'text-ink-gray-5'">
              {{ request.resolved_on
                ? __("Resolved {0}", [fmt(request.resolved_on)])
                : request.resolution_due_on ? __("Resolve by {0}", [fmt(request.resolution_due_on)]) : "" }}
            </span>
          </div>
        </div>
        <div v-else-if="!claim" class="text-ink-gray-5">
          {{ __("No KUMAR request behind this ticket.") }}
        </div>

        <!-- the claim -->
        <div v-if="claim" class="rounded-lg border p-3" :class="stage(claim.workflow_state).card">
          <div class="flex items-center justify-between gap-2">
            <span class="font-medium" :class="stage(claim.workflow_state).strong">{{ claim.name }}</span>
            <Badge :label="claim.workflow_state" :theme="claimTheme(claim.workflow_state)" variant="subtle" />
          </div>
          <div class="mt-0.5" :class="stage(claim.workflow_state).muted">
            {{ [claim.claim_type, claim.root_cause].filter(Boolean).join(" · ") }}
          </div>
          <div class="mt-1 tabular-nums" :class="stage(claim.workflow_state).muted">
            {{ __("Claimed") }} {{ money(claim.claim_amount) }}
            <span v-if="claim.approved_amount"> · {{ __("approved") }} {{ money(claim.approved_amount) }}</span>
            <span v-if="claim.settled_on"> · {{ __("settled") }} {{ fmt(claim.settled_on) }}</span>
          </div>
          <div v-if="claim.actions?.length" class="mt-2 flex flex-wrap gap-2">
            <Button
              v-for="a in claim.actions"
              :key="a.action"
              size="sm"
              variant="subtle"
              :theme="a.action === 'Reject' ? 'red' : a.action === 'Approve' || a.action === 'Settle' ? 'green' : 'gray'"
              :label="__(a.action)"
              @click="openAction(a)"
            />
          </div>
          <button
            v-if="claim.ticket && claim.ticket !== ticketName"
            class="mt-2 text-xs text-ink-gray-5 hover:underline"
            @click="router.push({ name: 'TicketAgent', params: { ticketId: claim.ticket } })"
          >
            {{ __("The claim has its own ticket #{0} - open it", [claim.ticket]) }}
          </button>
        </div>

        <!-- the visits -->
        <div>
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium uppercase tracking-wide text-ink-gray-5">{{ __("Visits") }}</span>
            <Button
              v-if="request || claim"
              size="sm"
              variant="ghost"
              :label="__('Schedule')"
              @click="openVisit"
            >
              <template #prefix><LucideCalendarPlus class="size-3.5" /></template>
            </Button>
          </div>
          <ul v-if="visits.length" class="mt-1 divide-y divide-outline-gray-1">
            <li v-for="v in visits" :key="v.name" class="py-1.5">
              <div class="flex items-center justify-between gap-2">
                <span class="tabular-nums text-ink-gray-8">{{ fmt(v.visit_date) }}</span>
                <Badge :label="visitState(v).label" :theme="visitState(v).theme" variant="subtle" />
              </div>
              <div class="text-xs text-ink-gray-6">
                {{ v.technician }} · {{ v.visit_type }}<span v-if="v.is_chargeable"> · {{ __("chargeable") }}</span>
              </div>
              <div v-if="v.docstatus === 1 && (v.findings || v.action_taken)" class="mt-0.5 line-clamp-2 text-xs text-ink-gray-5">
                {{ v.findings || v.action_taken }}
              </div>
            </li>
          </ul>
          <div v-else class="mt-1 text-ink-gray-5">{{ __("No visit yet.") }}</div>
        </div>
      </template>
    </div>
  </Section>

  <!-- book a technician; the dealer is told on the same thread -->
  <Dialog v-model="visiting" :options="{ title: __('Schedule a visit') }">
    <template #body-content>
      <div v-if="request" class="mb-3 rounded-lg border bg-surface-gray-1 p-3 text-sm text-ink-gray-7">
        {{ request.name }} · {{ ctx.data?.serial_no }}
      </div>
      <div v-else-if="claim" class="mb-3 rounded-lg border bg-surface-gray-1 p-3 text-sm text-ink-gray-7">
        {{ __("The claim has no service request yet; booking one opens it and links it to the claim.") }}
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
        :label="__('Book it and tell the dealer')" @click="submitVisit" />
    </template>
  </Dialog>

  <!-- move the claim; the dealer is told the outcome, and on a rejection the reason -->
  <Dialog v-model="acting" :options="{ title: actionTitle }">
    <template #body-content>
      <div v-if="claim" class="mb-4 rounded-lg border bg-surface-gray-1 p-3 text-sm">
        <div class="font-medium text-ink-gray-8">{{ claim.name }}</div>
        <div class="tabular-nums text-ink-gray-6">{{ __("claimed") }} {{ money(claim.claim_amount) }}</div>
      </div>
      <FormControl
        v-if="pending?.action === 'Approve'"
        v-model="amount"
        type="number"
        :label="__('Approve how much')"
        :description="__('Cannot exceed the {0} claimed.', [money(claim?.claim_amount)])"
      />
      <FormControl
        class="mt-3"
        v-model="remarks"
        type="textarea"
        :rows="3"
        :label="__('What should the dealer be told')"
        :placeholder="pending?.action === 'Reject' ? __('They are owed the reason, not just the outcome') : __('Optional')"
      />
      <ErrorMessage v-if="act.error" class="mt-3" :message="act.error" />
    </template>
    <template #actions>
      <Button class="w-full" variant="solid" :theme="pending?.action === 'Reject' ? 'red' : 'blue'"
        :loading="act.loading" :label="actionTitle" @click="act.submit()" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { ActivitiesSymbol, TicketSymbol } from "@/types";
import { useStorage } from "@vueuse/core";
import { Badge, Button, Dialog, ErrorMessage, FormControl, createResource, dayjs, toast } from "frappe-ui";
import LucideCalendarPlus from "~icons/lucide/calendar-plus";
import { computed, inject, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import Section from "../Section.vue";

const ticket = inject(TicketSymbol)!;
const activities = inject(ActivitiesSymbol)!;
const router = useRouter();
const ticketName = computed(() => String(ticket.value?.doc?.name || ""));
const opened = useStorage("kumarPanelOpened", true, localStorage);

const ctx = createResource({
  url: "kumar_service.staff_api.ticket_context",
  params: { ticket: ticketName.value },
  auto: true,
});
const request = computed(() => ctx.data?.request || null);
const claim = computed(() => ctx.data?.claim || null);
const visits = computed(() => ctx.data?.visits || []);

// after anything that writes to the thread, both the panel and the
// conversation are stale; the conversation is the activities resource
function refresh() {
  ctx.reload();
  activities.value?.reload?.();
}

// ---------------------------------------------------------------- display
function fmt(d: string) {
  return d ? dayjs(d).format("DD MMM YYYY") : "";
}
function overdue(d: string) {
  return !!d && dayjs(d).isBefore(dayjs());
}
function money(v: number) {
  return "₹" + Math.round(v || 0).toLocaleString("en-IN");
}
const warranty = computed(() => {
  const r = request.value;
  const exp = ctx.data?.site?.warranty_expiry_date;
  const inWarranty = r ? !!r.is_under_warranty : exp ? !dayjs(exp).isBefore(dayjs(), "day") : null;
  if (inWarranty === null) return { label: __("Warranty unknown"), theme: "gray" };
  return inWarranty ? { label: __("In warranty"), theme: "green" } : { label: __("Out of warranty"), theme: "red" };
});
function statusTheme(s: string) {
  return ({ Open: "orange", "In Progress": "blue", Resolved: "green", Closed: "gray", Cancelled: "gray" } as any)[s] || "gray";
}
function claimTheme(s: string) {
  return ({ "Pending Review": "orange", "Under Investigation": "blue", Approved: "green", Settled: "gray", Rejected: "red" } as any)[s] || "gray";
}
const STAGE: Record<string, any> = {
  "Pending Review": { card: "border-amber-200 bg-amber-50", strong: "text-amber-800", muted: "text-amber-700" },
  "Under Investigation": { card: "border-blue-200 bg-blue-50", strong: "text-blue-800", muted: "text-blue-700" },
  Approved: { card: "border-green-200 bg-green-50", strong: "text-green-800", muted: "text-green-700" },
};
function stage(s: string) {
  return STAGE[s] || { card: "border-outline-gray-2 bg-surface-white", strong: "text-ink-gray-9", muted: "text-ink-gray-5" };
}
function visitState(v: any) {
  if (v.docstatus === 1) return { label: __("Done"), theme: "gray" };
  if (v.upcoming) return { label: __("Booked"), theme: "blue" };
  return { label: __("Not closed"), theme: "orange" };
}
function openLookup() {
  router.push({ name: "KumarLookup", query: { serial: ctx.data?.serial_no } });
}

// ---------------------------------------------------------------- visits
const VISIT_TYPES = ["On-Site", "Workshop", "Telephonic"].map((v) => ({ label: __(v), value: v }));
const visiting = ref(false);
const visit = reactive({ technician: "", visit_date: "", visit_type: "On-Site", note: "" });
const technicianOptions = computed(() => [
  { label: __("Choose…"), value: "" },
  ...(ctx.data?.technicians || []).map((t: any) => ({
    label: t.dealer ? t.technician_name + " · " + t.dealer : t.technician_name,
    value: t.name,
  })),
]);
function openVisit() {
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
    refresh();
  },
};
const bookRequest = createResource({ url: "kumar_service.staff_api.schedule_visit", ...booked });
const bookClaim = createResource({ url: "kumar_service.staff_api.schedule_visit_for_claim", ...booked });
const bookError = computed(() => bookRequest.error || bookClaim.error);
function submitVisit() {
  const p = { technician: visit.technician, visit_date: visit.visit_date, visit_type: visit.visit_type, note: visit.note };
  if (request.value) bookRequest.submit({ service_request: request.value.name, ...p });
  else if (claim.value) bookClaim.submit({ claim: claim.value.name, ...p });
}

// ---------------------------------------------------------------- claim
const acting = ref(false);
const pending = ref<any>(null);
const amount = ref<number | null>(null);
const remarks = ref("");
const actionTitle = computed(() => (pending.value ? __(pending.value.action) + " " + (claim.value?.name || "") : ""));
function openAction(a: any) {
  pending.value = a;
  amount.value = claim.value?.claim_amount ?? null;
  remarks.value = "";
  acting.value = true;
}
const act = createResource({
  url: "kumar_service.staff_api.claim_action",
  makeParams: () => ({
    name: claim.value?.name,
    action: pending.value?.action,
    approved_amount: pending.value?.action === "Approve" ? amount.value : undefined,
    remarks: remarks.value,
  }),
  onSuccess: (d: any) => {
    acting.value = false;
    toast.success(d?.message || __("Done"));
    refresh();
  },
});
</script>
