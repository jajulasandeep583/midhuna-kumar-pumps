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

      <!-- which pump, which claim, whose: one box over the loaded board -->
      <div class="mb-4 flex flex-wrap items-center gap-2">
        <FormControl
          class="w-full sm:w-96"
          v-model="search"
          type="text"
          :placeholder="__('Serial, claim no, model, dealer or customer')"
          autocomplete="off"
        />
        <Button
          v-if="search || filter"
          variant="subtle"
          :label="__('Clear')"
          @click="search = ''; filter = ''"
        />
        <span v-if="search || filter" class="text-xs text-ink-gray-5">
          {{ __("{0} of {1} claims", [String(rows.length), String(board.data?.claims?.length || 0)]) }}
        </span>
      </div>

      <div v-if="board.loading && !board.data" class="py-12 text-center text-ink-gray-5">
        {{ __("Loading...") }}
      </div>
      <!-- an error must not masquerade as "nothing to decide" -->
      <div v-else-if="board.error" class="rounded-xl border border-red-200 bg-red-50 p-5 text-center">
        <p class="font-medium text-red-800">{{ __("The claims desk could not load.") }}</p>
        <ErrorMessage class="mt-1" :message="board.error" />
        <Button class="mt-3" variant="solid" theme="blue" :label="__('Try again')" @click="board.reload()" />
      </div>
      <div v-else-if="!rows.length" class="rounded-lg border border-dashed py-12 text-center text-ink-gray-5">
        {{ search || filter ? __("No claim matches that.") : __("No claim is waiting on a decision.") }}
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
            <ScheduleVisit
              :claim="c.name"
              :serial="c.serial_no"
              :technicians="visitBoard.data?.technicians"
              :label="__('Schedule a visit')"
              size="md"
              @done="board.reload()"
            />
          </div>

          <!-- the same component the ticket header uses, so deciding here and
               deciding there is literally the same buttons and dialog -->
          <ClaimDecision
            v-if="c.actions.length"
            class="mt-4 border-t pt-3"
            :claim="c"
            size="md"
            @done="board.reload()"
          />
          <p v-else class="mt-3 border-t pt-3 text-xs text-ink-gray-5">
            {{ __("Waiting on someone else - your roles cannot move this one.") }}
          </p>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Badge, Button, ErrorMessage, FormControl, createResource } from "frappe-ui";
import { money } from "@/utils/kumarTypes";
import { LayoutHeader } from "@/components";
import ClaimDecision from "@/components/ticket-agent/ClaimDecision.vue";
import ScheduleVisit from "@/components/ticket-agent/ScheduleVisit.vue";
import LucideMessageSquare from "~icons/lucide/message-square";
import { __ } from "@/translation";
import { useRouter } from "vue-router";

const router = useRouter();
const board = createResource({ url: "kumar_service.staff_api.claims_board", auto: true });

// technicians come from the visit board, which already knows who can go;
// the ScheduleVisit component on each card does the booking itself
const visitBoard = createResource({ url: "kumar_service.staff_api.visit_board", auto: true });
const filter = ref("");
const search = ref("");
// The board fetches only the OPEN states by default, so the Settled and
// Rejected tiles used to filter a list that could not contain them and came
// back empty. Clicking a tile now refetches with that state.
watch(filter, (s) => board.submit(s ? { state: s } : {}));

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
  let all = board.data?.claims || [];
  if (filter.value) all = all.filter((c: any) => c.workflow_state === filter.value);
  const q = search.value.trim().toLowerCase();
  if (q) {
    all = all.filter((c: any) =>
      [c.name, c.serial_no, c.pump_model, c.dealer, c.raised_by, c.customer,
        c.heat_no, c.winding_batch]
        .some((v: any) => v && String(v).toLowerCase().includes(q))
    );
  }
  return all;
});

function stateTheme(s: string) {
  if (s === "Approved") return "green";
  if (s === "Pending Review") return "orange";
  if (s === "Rejected") return "red";
  return "blue";
}

</script>
