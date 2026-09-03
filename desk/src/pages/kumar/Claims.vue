<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ __("Warranty Claims") }}</div>
      </template>
      <template #right-header>
        <Button variant="ghost" :label="__('Refresh')" @click="board.reload()" />
      </template>
    </LayoutHeader>

    <div class="px-5 py-5">
      <!-- money by stage: the reason a manager opens this page ------------- -->
      <div class="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <button
          v-for="s in stages"
          :key="s.state"
          class="rounded-xl border p-4 text-left transition hover:shadow-md"
          :class="[s.card, filter === s.state ? 'ring-2 ring-blue-400' : '']"
          @click="filter = filter === s.state ? '' : s.state"
        >
          <div class="text-xs font-medium" :class="s.muted">{{ __(s.state) }}</div>
          <div class="mt-1 text-2xl font-semibold tabular-nums" :class="s.strong">
            {{ s.count }}
          </div>
          <div class="mt-0.5 text-xs tabular-nums" :class="s.muted">{{ money(s.value) }}</div>
        </button>
      </div>

      <div v-if="board.loading && !board.data" class="py-12 text-center text-ink-gray-5">
        {{ __("Loading...") }}
      </div>
      <div v-else-if="!rows.length" class="rounded-lg border border-dashed py-12 text-center text-ink-gray-5">
        {{ __("No claim is waiting on a decision.") }}
      </div>

      <div v-else class="space-y-3">
        <div v-for="c in rows" :key="c.name" class="rounded-xl border bg-surface-white p-4 shadow-sm">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="font-semibold tabular-nums text-ink-gray-9">{{ c.name }}</span>
                <Badge :theme="stateTheme(c.workflow_state)" :label="__(c.workflow_state)" />
                <span class="text-sm text-ink-gray-6">{{ __(c.claim_type) }}</span>
              </div>
              <div class="mt-1 text-sm text-ink-gray-7">
                <span class="tabular-nums">{{ c.serial_no }}</span>
                <span v-if="c.pump_model"> · {{ c.pump_model }}</span>
              </div>
              <!-- who is asking, and who the pump belongs to -->
              <div class="mt-1 text-sm">
                <span class="text-ink-gray-5">{{ __("Raised by") }}</span>
                <span class="text-ink-gray-8"> {{ c.raised_by || c.dealer }}</span>
                <template v-if="c.customer">
                  <span class="text-ink-gray-5"> · {{ __("for") }}</span>
                  <span class="text-ink-gray-8"> {{ c.customer }}</span>
                  <a v-if="c.customer_mobile" :href="`tel:${c.customer_mobile}`"
                     class="ml-1 tabular-nums text-ink-blue-6 hover:underline">{{ c.customer_mobile }}</a>
                </template>
              </div>
              <div class="mt-0.5 text-xs text-ink-gray-5">
                <span v-if="c.where">{{ c.where }}<span v-if="c.district">, {{ c.district }}</span> · </span>
                {{ __("claimed") }} {{ String(c.claim_date || c.creation).slice(0, 10) }}
              </div>
            </div>
            <div class="text-right">
              <div class="text-xl font-semibold tabular-nums text-ink-gray-9">
                {{ money(c.approved_amount || c.claim_amount) }}
              </div>
              <div v-if="c.approved_amount && c.approved_amount != c.claim_amount"
                   class="text-xs tabular-nums text-ink-gray-5">
                {{ __("claimed") }} {{ money(c.claim_amount) }}
              </div>
            </div>
          </div>

          <!-- the evidence the decision rests on -->
          <div v-if="c.technician_report" class="mt-3 rounded-lg bg-surface-gray-1 p-3 text-sm text-ink-gray-7">
            {{ c.technician_report }}
          </div>
          <div class="mt-2 flex flex-wrap gap-4 text-xs text-ink-gray-5">
            <span v-if="c.root_cause">{{ __("Root cause") }}: <b class="text-ink-gray-7">{{ __(c.root_cause) }}</b></span>
            <span v-if="c.heat_no">{{ __("Heat") }}: <b class="tabular-nums text-ink-gray-7">{{ c.heat_no }}</b></span>
            <span v-if="c.winding_batch">{{ __("Winding") }}: <b class="tabular-nums text-ink-gray-7">{{ c.winding_batch }}</b></span>
          </div>

          <!-- The conversation is the same full ticket screen every request
               uses - dealer on one side, KUMAR on the other, photographs
               shown as photographs. A chat box inside this card was a second
               thread nobody could find afterwards. -->
          <div class="mt-3 flex flex-wrap gap-2 border-t pt-3">
            <Button
              variant="subtle"
              :label="__('Open conversation')"
              :disabled="!c.ticket"
              @click="c.ticket && router.push({ name: 'TicketAgent', params: { ticketId: c.ticket } })"
            >
              <template #prefix><LucideMessageSquare class="size-4" /></template>
            </Button>
            <Button
              variant="subtle"
              :label="__('Schedule a visit')"
              @click="openVisit(c)"
            >
              <template #prefix><LucideCalendarCheck class="size-4" /></template>
            </Button>
          </div>

          <div v-if="c.actions.length" class="mt-4 flex flex-wrap gap-2 border-t pt-3">
            <Button
              v-for="a in c.actions"
              :key="a.action"
              :variant="a.action === 'Reject' ? 'subtle' : 'solid'"
              :theme="a.action === 'Reject' ? 'red' : 'blue'"
              :label="actionLabel(a.action)"
              @click="open(c, a)"
            />
          </div>
          <p v-else class="mt-3 border-t pt-3 text-xs text-ink-gray-5">
            {{ __("Waiting on someone else - your roles cannot move this one.") }}
          </p>
        </div>
      </div>
    </div>

    <Dialog v-model="visiting" :options="{ title: __('Schedule a visit') }">
      <template #body-content>
        <div v-if="visitFor" class="mb-4 rounded-lg border bg-surface-gray-1 p-3 text-sm">
          <div class="font-medium text-ink-gray-8">{{ visitFor.name }} · {{ visitFor.serial_no }}</div>
          <div class="text-ink-gray-6">{{ [visitFor.customer, visitFor.where].filter(Boolean).join(" · ") }}</div>
        </div>
        <FormControl v-model="visit.technician" type="select" :label="__('Technician')" :options="technicianOptions" />
        <FormControl class="mt-3" v-model="visit.visit_date" type="date" :label="__('Date')" />
        <FormControl class="mt-3" v-model="visit.note" type="textarea" :rows="2"
                     :label="__('Anything to tell the dealer')" />
        <ErrorMessage v-if="book.error" class="mt-3" :message="book.error" />
      </template>
      <template #actions>
        <Button class="w-full" variant="solid" theme="blue" :loading="book.loading"
                :disabled="!visit.technician || !visit.visit_date"
                :label="__('Book it and tell the dealer')" @click="book.submit()" />
      </template>
    </Dialog>

    <Dialog v-model="showing" :options="{ title: dialogTitle }">
      <template #body-content>
        <div v-if="target" class="mb-4 rounded-lg border bg-surface-gray-1 p-3 text-sm">
          <div class="font-medium text-ink-gray-8">{{ target.name }} · {{ target.dealer }}</div>
          <div class="tabular-nums text-ink-gray-6">
            {{ target.serial_no }} · {{ __("claimed") }} {{ money(target.claim_amount) }}
          </div>
        </div>

        <FormControl
          v-if="pending?.action === 'Approve'"
          v-model="amount"
          type="number"
          :label="__('Approve how much')"
          :description="__('Cannot exceed the {0} claimed.', [money(target?.claim_amount)])"
        />
        <FormControl
          class="mt-3"
          v-model="remarks"
          type="textarea"
          :rows="3"
          :label="__('What should the dealer be told')"
          :placeholder="pending?.action === 'Reject'
            ? __('They are owed the reason, not just the outcome')
            : __('Optional')"
        />
        <ErrorMessage v-if="act.error" class="mt-3" :message="act.error" />
      </template>
      <template #actions>
        <Button
          class="w-full"
          variant="solid"
          :theme="pending?.action === 'Reject' ? 'red' : 'blue'"
          :loading="act.loading"
          :label="dialogTitle"
          @click="act.submit()"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { Badge, Button, Dialog, ErrorMessage, FormControl, createResource, toast } from "frappe-ui";
import { LayoutHeader } from "@/components";
import LucideMessageSquare from "~icons/lucide/message-square";
import LucideCalendarCheck from "~icons/lucide/calendar-check";
import { __ } from "@/translation";
import { useRouter } from "vue-router";

const router = useRouter();
const board = createResource({ url: "kumar_service.staff_api.claims_board", auto: true });

// technicians come from the visit board, which already knows who can go
const visitBoard = createResource({ url: "kumar_service.staff_api.visit_board", auto: true });
const technicianOptions = computed(() => [
  { label: __("Choose a technician"), value: "" },
  ...(visitBoard.data?.technicians || []).map((t: any) => ({
    label: [t.technician_name || t.name, t.dealer].filter(Boolean).join(" · "),
    value: t.name,
  })),
]);
const visiting = ref(false);
const visitFor = ref<any>(null);
const visit = reactive({ technician: "", visit_date: "", note: "" });
function openVisit(c: any) {
  visitFor.value = c;
  visit.technician = "";
  visit.visit_date = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
  visit.note = "";
  visiting.value = true;
}
const book = createResource({
  url: "kumar_service.staff_api.schedule_visit_for_claim",
  makeParams: () => ({
    claim: visitFor.value?.name,
    technician: visit.technician,
    visit_date: visit.visit_date,
    note: visit.note,
  }),
  onSuccess: (d: any) => {
    visiting.value = false;
    toast.success(d.message);
    board.reload();
  },
});
const filter = ref("");
const showing = ref(false);
const target = ref<any>(null);
const pending = ref<any>(null);
const amount = ref<number | null>(null);
const remarks = ref("");

function money(v: number) {
  return "₹" + Math.round(v || 0).toLocaleString("en-IN");
}

const STAGE_STYLE: Record<string, any> = {
  "Pending Review": {
    card: "border-amber-200 bg-amber-50", strong: "text-amber-800", muted: "text-amber-700",
  },
  "Under Investigation": {
    card: "border-blue-200 bg-blue-50", strong: "text-blue-800", muted: "text-blue-700",
  },
  Approved: {
    card: "border-green-200 bg-green-50", strong: "text-green-800", muted: "text-green-700",
  },
  Settled: {
    card: "border-outline-gray-2 bg-surface-white", strong: "text-ink-gray-9", muted: "text-ink-gray-5",
  },
  Rejected: {
    card: "border-outline-gray-2 bg-surface-white", strong: "text-ink-gray-9", muted: "text-ink-gray-5",
  },
};

const stages = computed(() =>
  Object.entries(board.data?.totals || {}).map(([state, t]: any) => ({
    state,
    count: t.count,
    value: t.value,
    ...(STAGE_STYLE[state] || STAGE_STYLE.Settled),
  }))
);

const rows = computed(() => {
  const all = board.data?.claims || [];
  return filter.value ? all.filter((c: any) => c.workflow_state === filter.value) : all;
});

function stateTheme(s: string) {
  if (s === "Approved") return "green";
  if (s === "Pending Review") return "orange";
  if (s === "Rejected") return "red";
  return "blue";
}

function actionLabel(a: string) {
  return {
    Review: __("Send for investigation"),
    Approve: __("Approve"),
    Reject: __("Reject"),
    Settle: __("Mark settled"),
  }[a] || __(a);
}

const dialogTitle = computed(() => (pending.value ? actionLabel(pending.value.action) : ""));

function open(claim: any, action: any) {
  target.value = claim;
  pending.value = action;
  amount.value = claim.approved_amount || claim.claim_amount;
  remarks.value = "";
  showing.value = true;
}

const act = createResource({
  url: "kumar_service.staff_api.claim_action",
  makeParams: () => ({
    name: target.value?.name,
    action: pending.value?.action,
    approved_amount: pending.value?.action === "Approve" ? amount.value : undefined,
    remarks: remarks.value,
  }),
  onSuccess: (d: any) => {
    showing.value = false;
    toast.success(d.message);
    board.reload();
  },
});
</script>
