<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ __("Raise for a Pump") }}</div>
      </template>
    </LayoutHeader>

    <div class="mx-auto max-w-4xl px-5 py-6">
      <p class="mb-4 text-sm text-ink-gray-6">
        {{ __("Whoever rang or wrote in - find their pump, then raise the request, lodge the claim or book the visit from here. It lands on the ticket, and the dealer is told.") }}
      </p>

      <!-- 1. the pump ----------------------------------------------------- -->
      <div class="flex items-end gap-2">
        <FormControl
          class="flex-1"
          v-model="q"
          type="text"
          :label="__('Find the pump')"
          :placeholder="__('Serial, customer name, phone, dealer, district or invoice')"
          autocomplete="off"
          @input="search()"
          @keydown.enter.prevent="search(true)"
        />
        <ScanButton @scanned="(v) => pick(v)" />
      </div>
      <ul v-if="hits.data?.length && !picked" class="mt-2 divide-y rounded-lg border bg-surface-white">
        <li
          v-for="h in hits.data"
          :key="h.serial_no"
          class="flex cursor-pointer items-center justify-between gap-3 px-3 py-2.5 hover:bg-surface-gray-2"
          @click="pick(h.serial_no)"
        >
          <div class="min-w-0">
            <div class="font-medium tabular-nums text-ink-gray-9">{{ h.serial_no }}
              <span class="font-normal text-ink-gray-6"> · {{ h.pump_model }}</span></div>
            <div class="truncate text-xs text-ink-gray-6">
              {{ [h.end_customer_name, h.end_customer_mobile, h.dealer, h.district].filter(Boolean).join(" · ") || __("Not registered - no customer on record") }}
            </div>
          </div>
          <Badge :label="h.warranty_status" :theme="warrantyTheme(h.warranty_status)" variant="subtle" />
        </li>
      </ul>
      <div v-else-if="q.length >= 2 && hits.data && !hits.data.length && !hits.loading && !picked" class="mt-2 text-sm text-ink-gray-5">
        {{ __("No pump matches. Check the serial on the nameplate, or register the sale first.") }}
      </div>
      <ErrorMessage v-if="ctx.error" class="mt-2" :message="ctx.error" />

      <!-- the pump, once chosen -->
      <div v-if="pump" class="mt-5 rounded-xl border p-4" :class="verdict.card">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div class="flex items-center gap-2">
              <span class="text-lg font-semibold tabular-nums text-ink-gray-9">{{ pump.serial_no }}</span>
              <Badge :label="pump.warranty_status" :theme="warrantyTheme(pump.warranty_status)" variant="subtle" />
            </div>
            <div class="text-sm text-ink-gray-7">
              {{ pump.pump_model }}<span v-if="pump.hp"> · {{ pump.hp }} HP</span><span v-if="pump.dealer"> · {{ pump.dealer }}</span>
            </div>
            <div class="mt-1 text-sm text-ink-gray-6">
              <template v-if="pump.end_customer_name">
                {{ pump.end_customer_name }}<span v-if="pump.end_customer_mobile"> · {{ pump.end_customer_mobile }}</span>
              </template>
              <template v-else>{{ __("No customer on record") }}</template>
              <span v-if="pump.warranty_expiry_date"> · {{ __("warranty till") }} {{ pump.warranty_expiry_date }}</span>
            </div>
          </div>
          <div class="flex gap-2">
            <Button variant="ghost" :label="__('Lookup')" @click="router.push({ name: 'KumarLookup', query: { serial: pump.serial_no } })" />
            <Button variant="ghost" :label="__('Change pump')" @click="clear()" />
          </div>
        </div>
        <!-- what is already open, so nothing is raised twice -->
        <div v-if="openRequests.length || openClaims.length" class="mt-3 flex flex-wrap gap-2 text-xs">
          <button
            v-for="r in openRequests" :key="r.name"
            class="rounded-full border bg-surface-white px-2.5 py-1 text-ink-gray-7 hover:bg-surface-gray-2"
            :title="__('Open the ticket')"
            @click="r.ticket && router.push({ name: 'TicketAgent', params: { ticketId: r.ticket } })"
          >{{ r.name }} · {{ r.custom_request_type || r.complaint_category }} · {{ r.status }}</button>
          <button
            v-for="c in openClaims" :key="c.name"
            class="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-amber-800 hover:bg-amber-100"
            :title="__('Open the ticket')"
            @click="c.ticket && router.push({ name: 'TicketAgent', params: { ticketId: c.ticket } })"
          >{{ c.name }} · {{ c.workflow_state }}</button>
        </div>
      </div>

      <!-- 2. what to raise --------------------------------------------------- -->
      <template v-if="pump">
        <div class="mt-5 inline-flex rounded-lg border bg-surface-gray-1 p-1 text-sm">
          <button
            v-for="m in MODES" :key="m.key"
            class="rounded-md px-3 py-1.5 font-medium transition-colors"
            :class="mode === m.key ? 'bg-surface-white text-ink-gray-9 shadow-sm' : 'text-ink-gray-6 hover:text-ink-gray-8'"
            @click="mode = m.key"
          >{{ m.label }}</button>
        </div>

        <div class="mt-4 rounded-xl border bg-surface-white p-5">
          <!-- how it reached KUMAR: stamped on the request and shown on the ticket -->
          <div class="mb-4 flex flex-wrap items-center gap-2 border-b pb-4">
            <span class="text-sm text-ink-gray-6">{{ __("Reached you via") }}</span>
            <button
              v-for="c in options.data?.channels || []" :key="c"
              class="rounded-full border px-3 py-1 text-sm transition-colors"
              :class="channel === c ? 'border-blue-600 bg-blue-50 text-blue-800' : 'text-ink-gray-7 hover:bg-surface-gray-2'"
              @click="channel = c"
            >{{ __(c) }}</button>
          </div>
          <!-- a request -->
          <div v-if="mode === 'request'" class="space-y-3">
            <div class="grid gap-3 sm:grid-cols-3">
              <FormControl v-model="req.request_type" type="select" :label="__('Type')" :options="opt('request_types')" />
              <FormControl v-model="req.complaint_category" type="select" :label="__('What is wrong')" :options="opt('complaint_categories')" />
              <FormControl v-model="req.priority" type="select" :label="__('Priority')" :options="opt('priorities')" />
            </div>
            <FormControl v-model="req.description" type="textarea" :rows="4"
              :label="__('What was reported')" :placeholder="__('In the caller\'s words: what the pump does, since when, what they have tried.')" />
            <Attachments v-model="files" />
            <ErrorMessage v-if="sendRequest.error" :message="sendRequest.error" />
            <div class="flex items-center justify-between">
              <span class="text-xs text-ink-gray-5">
                {{ pump.is_under_warranty ? __("In warranty: the visit will be free.") : __("Out of warranty: the visit is chargeable.") }}
              </span>
              <Button variant="solid" theme="blue" :loading="sendRequest.loading"
                :disabled="!req.description.trim() || !req.complaint_category"
                :label="__('Raise the request')" @click="sendRequest.submit()" />
            </div>
          </div>

          <!-- a claim -->
          <div v-else-if="mode === 'claim'" class="space-y-3">
            <div v-if="!pump.dealer" class="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              {{ __("This pump has no dealer on record. A claim is settled with a dealer - register the sale first.") }}
            </div>
            <div class="grid gap-3 sm:grid-cols-3">
              <FormControl v-model="clm.claim_type" type="select" :label="__('Claim type')" :options="opt('claim_types')" />
              <FormControl v-model="clm.claim_amount" type="number" :label="__('Amount claimed (₹)')" />
              <FormControl v-model="clm.root_cause" type="select" :label="__('Root cause, if known')" :options="opt('root_causes', true)" />
            </div>
            <FormControl v-model="clm.service_request" type="select" :label="__('Against a request already open on this pump')"
              :options="requestOptions" />
            <FormControl v-model="clm.technician_report" type="textarea" :rows="4"
              :label="__('What failed')" :placeholder="__('The dealer\'s or technician\'s account of the failure.')" />
            <Attachments v-model="files" />
            <ErrorMessage v-if="sendClaim.error" :message="sendClaim.error" />
            <div class="flex items-center justify-between">
              <span class="text-xs text-ink-gray-5">{{ __("Goes to Pending Review; the dealer is told it was opened for them.") }}</span>
              <Button variant="solid" theme="blue" :loading="sendClaim.loading"
                :disabled="!pump.dealer || !clm.technician_report.trim()"
                :label="__('Lodge the claim')" @click="sendClaim.submit()" />
            </div>
          </div>

          <!-- a visit -->
          <div v-else class="space-y-3">
            <FormControl v-model="vis.service_request" type="select" :label="__('For which request')" :options="visitRequestOptions" />
            <FormControl v-if="!vis.service_request" v-model="vis.reason" type="textarea" :rows="2"
              :label="__('What the visit is for')" :placeholder="__('A request is opened for it, typed as a visit.')" />
            <div class="grid gap-3 sm:grid-cols-3">
              <FormControl v-model="vis.technician" type="select" :label="__('Technician')" :options="technicianOptions" />
              <FormControl v-model="vis.visit_date" type="date" :label="__('Date')" />
              <FormControl v-model="vis.visit_type" type="select" :label="__('Type')" :options="opt('visit_types')" />
            </div>
            <FormControl v-model="vis.note" type="textarea" :rows="2" :label="__('Anything the dealer should know')" :placeholder="__('Optional')" />
            <ErrorMessage v-if="sendVisit.error" :message="sendVisit.error" />
            <div class="flex items-center justify-between">
              <span class="text-xs text-ink-gray-5">{{ __("The dealer is told the date and the technician on the thread.") }}</span>
              <Button variant="solid" theme="blue" :loading="sendVisit.loading"
                :disabled="!vis.technician || !vis.visit_date || (!vis.service_request && !vis.reason.trim())"
                :label="__('Book the visit')" @click="sendVisit.submit()" />
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";
import { Badge, Button, ErrorMessage, FormControl, createResource, toast } from "frappe-ui";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import Attachments from "./Attachments.vue";
import ScanButton from "./ScanButton.vue";

const router = useRouter();
const route = useRoute();

const MODES = [
  { key: "request", label: __("Request") },
  { key: "claim", label: __("Warranty claim") },
  { key: "visit", label: __("Visit") },
];
const mode = ref<string>("request");
const channel = ref<string>("Phone");

// ---------------------------------------------------------------- the pump
const q = ref("");
const picked = ref("");
let timer: any = null;
const hits = createResource({
  url: "kumar_service.staff_api.find_pumps",
  makeParams: () => ({ q: q.value }),
});
function search(now = false) {
  picked.value = "";
  clearTimeout(timer);
  if (q.value.trim().length < 2) { hits.data = []; return; }
  timer = setTimeout(() => hits.submit(), now ? 0 : 250);
}
const ctx = createResource({
  url: "kumar_service.staff_api.pump_context",
  makeParams: () => ({ serial_no: picked.value }),
  onSuccess: () => {
    // remember where we were: reload lands on the same pump
    router.replace({ query: { ...route.query, serial: picked.value } });
  },
});
const pump = computed(() => (picked.value && ctx.data?.pump) || null);
const openRequests = computed(() => ctx.data?.open_requests || []);
const openClaims = computed(() => ctx.data?.open_claims || []);
function pick(serial: string) {
  const s = (serial || "").trim();
  if (!s) return;
  picked.value = s;
  q.value = s;
  hits.data = [];
  ctx.submit();
}
function clear() {
  picked.value = "";
  ctx.data = null;
  q.value = "";
  router.replace({ query: { ...route.query, serial: undefined } });
}

// ---------------------------------------------------------------- options
const options = createResource({ url: "kumar_service.staff_api.raise_options", auto: true });
function opt(key: string, blankFirst = false) {
  const list: string[] = options.data?.[key] || [];
  const out = list.map((v) => ({ label: __(v), value: v }));
  return blankFirst ? [{ label: __("Not known yet"), value: "" }, ...out] : out;
}
const technicianOptions = computed(() => [
  { label: __("Choose…"), value: "" },
  ...(options.data?.technicians || []).map((t: any) => ({
    label: t.dealer ? t.technician_name + " · " + t.dealer : t.technician_name,
    value: t.name,
  })),
]);
const requestOptions = computed(() => [
  { label: __("None - a standalone claim"), value: "" },
  ...openRequests.value.map((r: any) => ({ label: r.name + " · " + (r.custom_request_type || r.complaint_category) + " · " + r.status, value: r.name })),
]);
const visitRequestOptions = computed(() => [
  { label: __("A new one - say what it is for"), value: "" },
  ...openRequests.value.map((r: any) => ({ label: r.name + " · " + (r.custom_request_type || r.complaint_category) + " · " + r.status, value: r.name })),
]);
// sensible defaults once the option lists arrive
watch(() => options.data, (d) => {
  if (!d) return;
  if (!req.request_type) req.request_type = d.request_types?.includes("Complaint") ? "Complaint" : d.request_types?.[0] || "";
  if (!req.complaint_category) req.complaint_category = d.complaint_categories?.[0] || "";
  if (!req.priority) req.priority = d.priorities?.includes("Medium") ? "Medium" : d.priorities?.[0] || "";
  if (!clm.claim_type) clm.claim_type = d.claim_types?.[0] || "";
  if (!vis.visit_type) vis.visit_type = d.visit_types?.[0] || "";
});
// the most recent open request is the likely one a visit is for
watch(openRequests, (list) => { if (!vis.service_request && list.length) vis.service_request = list[0].name; });

// ---------------------------------------------------------------- the forms
const files = ref<any[]>([]);
const req = reactive({ request_type: "", complaint_category: "", priority: "", description: "" });
const clm = reactive({ claim_type: "", claim_amount: null as number | null, root_cause: "", service_request: "", technician_report: "" });
const vis = reactive({ service_request: "", reason: "", technician: "", visit_date: tomorrow(), visit_type: "", note: "" });
function tomorrow() { return new Date(Date.now() + 86400000).toISOString().slice(0, 10); }
function attachments() { return files.value.map((f) => ({ filename: f.filename, content: f.content })); }
function landed(d: any, fallback: string) {
  toast.success(d?.message || fallback);
  files.value = [];
  if (d?.ticket) router.push({ name: "TicketAgent", params: { ticketId: d.ticket } });
  else ctx.reload();
}
const sendRequest = createResource({
  url: "kumar_service.staff_api.raise_request_for_pump",
  makeParams: () => ({ serial_no: picked.value, request_type: req.request_type, complaint_category: req.complaint_category,
    description: req.description, priority: req.priority, attachments: attachments(), channel: channel.value }),
  onSuccess: (d: any) => landed(d, __("Request raised")),
});
const sendClaim = createResource({
  url: "kumar_service.staff_api.raise_claim_for_pump",
  makeParams: () => ({ serial_no: picked.value, claim_type: clm.claim_type, claim_amount: clm.claim_amount || 0,
    technician_report: clm.technician_report, root_cause: clm.root_cause || null, service_request: clm.service_request || null,
    attachments: attachments(), channel: channel.value }),
  onSuccess: (d: any) => landed(d, __("Claim lodged")),
});
const sendVisit = createResource({
  url: "kumar_service.staff_api.schedule_visit_for_pump",
  makeParams: () => ({ serial_no: picked.value, technician: vis.technician, visit_date: vis.visit_date, visit_type: vis.visit_type,
    note: vis.note, service_request: vis.service_request || null, reason: vis.reason, channel: channel.value }),
  onSuccess: (d: any) => landed(d, __("Visit booked")),
});

// ---------------------------------------------------------------- display
const verdict = computed(() => {
  const s = pump.value?.warranty_status;
  if (s === "In Warranty") return { card: "border-green-200 bg-green-50" };
  if (s === "Expiring Soon") return { card: "border-amber-200 bg-amber-50" };
  if (s === "Expired") return { card: "border-red-200 bg-red-50" };
  return { card: "border-outline-gray-2 bg-surface-gray-1" };
});
function warrantyTheme(s: string) {
  return ({ "In Warranty": "green", "Expiring Soon": "orange", Expired: "red" } as any)[s] || "gray";
}

onMounted(() => {
  const s = route.query.serial;
  if (typeof s === "string" && s) pick(s);
  const m = route.query.mode;
  if (typeof m === "string" && MODES.some((x) => x.key === m)) mode.value = m;
});
</script>
