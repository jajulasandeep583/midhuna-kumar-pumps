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

          <!-- the conversation, and whatever the dealer photographed ------ -->
          <div class="mt-3 border-t pt-3">
            <Button
              variant="ghost"
              :label="openThread === c.name ? __('Hide conversation') : __('Conversation')"
              @click="toggleThread(c)"
            >
              <template #suffix>
                <span v-if="threadCount(c)" class="rounded bg-surface-gray-3 px-1.5 text-xs tabular-nums">
                  {{ threadCount(c) }}
                </span>
              </template>
            </Button>

            <div v-if="openThread === c.name" class="mt-3">
              <div v-if="thread.loading" class="py-3 text-sm text-ink-gray-5">{{ __("Loading...") }}</div>
              <div v-else-if="!messages.length" class="py-3 text-sm text-ink-gray-5">
                {{ __("Nothing said yet.") }}
              </div>

              <div v-else class="space-y-2">
                <div
                  v-for="m in messages"
                  :key="m.name"
                  class="flex"
                  :class="m.from_dealer ? 'justify-start' : 'justify-end'"
                >
                  <div
                    class="max-w-[85%] rounded-lg px-3 py-2 text-sm"
                    :class="m.from_dealer
                      ? 'bg-surface-gray-2 text-ink-gray-8'
                      : 'bg-blue-600 text-white'"
                  >
                    <div class="mb-0.5 text-[11px] opacity-80">{{ m.who }} · {{ when(m.on) }}</div>
                    <div class="whitespace-pre-wrap">{{ m.message }}</div>

                    <!-- photographs are the evidence; show them, do not link to them -->
                    <div v-if="m.attachments?.length" class="mt-2 flex flex-wrap gap-2">
                      <a
                        v-for="f in m.attachments"
                        :key="f.url || f.file_url"
                        :href="f.url || f.file_url"
                        target="_blank"
                        rel="noopener"
                        class="block"
                      >
                        <img
                          v-if="isImage(f)"
                          :src="f.url || f.file_url"
                          :alt="f.name || f.file_name"
                          class="size-20 rounded border border-white/30 object-cover"
                        />
                        <span
                          v-else
                          class="flex items-center gap-1 rounded border px-2 py-1 text-xs"
                          :class="m.from_dealer ? 'border-outline-gray-2' : 'border-white/40'"
                        >
                          <LucidePaperclip class="size-3" />
                          {{ f.name || f.file_name }}
                        </span>
                      </a>
                    </div>
                  </div>
                </div>
              </div>

              <div class="mt-3">
                <FormControl
                  v-model="reply"
                  type="textarea"
                  :rows="2"
                  :placeholder="__('Write to the dealer - they read this on a phone')"
                />

                <ul v-if="outFiles.length" class="mt-2 flex flex-wrap gap-2">
                  <li
                    v-for="(f, i) in outFiles"
                    :key="f.filename + i"
                    class="flex items-center gap-2 rounded border bg-surface-white px-2 py-1 text-xs"
                  >
                    <img v-if="f.preview" :src="f.preview" alt="" class="size-8 rounded object-cover" />
                    <LucidePaperclip v-else class="size-3 text-ink-gray-5" />
                    <span class="max-w-40 truncate text-ink-gray-7">{{ f.filename }}</span>
                    <span class="tabular-nums text-ink-gray-5">{{ f.size }}</span>
                    <button class="text-ink-gray-5 hover:text-ink-red-3" @click="outFiles.splice(i, 1)">×</button>
                  </li>
                </ul>
                <ErrorMessage v-if="outError" class="mt-2" :message="outError" />

                <div class="mt-2 flex items-center justify-between gap-2">
                  <!-- KUMAR sends evidence back too: a marked-up photo, a credit
                       note, the bench test sheet -->
                  <label class="flex cursor-pointer items-center gap-1.5 text-sm text-ink-gray-6 hover:text-ink-gray-8">
                    <LucidePaperclip class="size-4" />
                    {{ __("Attach a photo or file") }}
                    <input
                      type="file"
                      class="hidden"
                      multiple
                      accept="image/*,video/*,application/pdf"
                      @change="addOutFiles"
                    />
                  </label>
                  <Button
                    variant="solid"
                    theme="blue"
                    :loading="send.loading"
                    :disabled="!reply.trim() && !outFiles.length"
                    :label="__('Send')"
                    @click="send.submit()"
                  />
                </div>
              </div>
              <ErrorMessage v-if="send.error" class="mt-2" :message="send.error" />
            </div>
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
import { computed, ref } from "vue";
import { Badge, Button, Dialog, ErrorMessage, FormControl, createResource, toast } from "frappe-ui";
import { LayoutHeader } from "@/components";
import LucidePaperclip from "~icons/lucide/paperclip";
import { __ } from "@/translation";

const board = createResource({ url: "kumar_service.staff_api.claims_board", auto: true });
const filter = ref("");
const showing = ref(false);
const target = ref<any>(null);
const pending = ref<any>(null);
const amount = ref<number | null>(null);
const remarks = ref("");
const openThread = ref("");
const reply = ref("");
const counts = ref<Record<string, number>>({});

// Matches MAX_ATTACHMENT_MB on the server. Checked here too so nobody uploads
// for a minute to be refused at the end of it.
const MAX_MB = 8;
const outFiles = ref<any[]>([]);
const outError = ref("");

function human(bytes: number) {
  return bytes > 1024 * 1024
    ? (bytes / 1024 / 1024).toFixed(1) + " MB"
    : Math.max(1, Math.round(bytes / 1024)) + " KB";
}

async function addOutFiles(e: Event) {
  outError.value = "";
  const picked = Array.from((e.target as HTMLInputElement).files || []);
  for (const file of picked) {
    if (file.size > MAX_MB * 1024 * 1024) {
      outError.value = __("{0} is too large. The limit is {1} MB.", [file.name, String(MAX_MB)]);
      continue;
    }
    const content = await new Promise<string>((resolve) => {
      const r = new FileReader();
      r.onload = () => resolve(String(r.result).split(",")[1] || "");
      r.readAsDataURL(file);
    });
    outFiles.value.push({
      filename: file.name,
      content,
      size: human(file.size),
      preview: file.type.startsWith("image/") ? URL.createObjectURL(file) : "",
    });
  }
  (e.target as HTMLInputElement).value = "";
}

// the server sends a full timestamp with microseconds; nobody reads that
function when(v: string) {
  if (!v) return "";
  const d = new Date(String(v).replace(" ", "T"));
  if (isNaN(d.getTime())) return String(v).slice(0, 16);
  return d.toLocaleString("en-IN", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: true,
  });
}

const thread = createResource({
  url: "kumar_service.staff_api.conversation",
  onSuccess: (d: any) => {
    counts.value[d.name] = (d.thread || []).length;
  },
});
const messages = computed(() => thread.data?.thread || []);

function threadCount(c: any) {
  return counts.value[c.name];
}

function toggleThread(c: any) {
  if (openThread.value === c.name) {
    openThread.value = "";
    return;
  }
  openThread.value = c.name;
  reply.value = "";
  thread.submit({ kind: "claim", name: c.name });
}

function isImage(f: any) {
  // the server already decided this; the extension check is only a fallback for
  // a row that predates the flag
  if (f.is_image !== undefined) return !!f.is_image;
  const n = String(f.file_name || f.file_url || "").toLowerCase();
  return /\.(jpe?g|png|gif|webp|heic|bmp)$/.test(n);
}

// mark_responded stops the SLA response clock, which is the whole reason a
// reply goes through this endpoint rather than into a comment box
const send = createResource({
  url: "kumar_service.staff_api.reply_to_dealer",
  makeParams: () => ({
    kind: "claim",
    name: openThread.value,
    message: reply.value || __("(photo attached)"),
    mark_responded: 1,
    attachments: outFiles.value.map((f) => ({ filename: f.filename, content: f.content })),
  }),
  onSuccess: () => {
    reply.value = "";
    outFiles.value.forEach((f) => f.preview && URL.revokeObjectURL(f.preview));
    outFiles.value = [];
    outError.value = "";
    thread.submit({ kind: "claim", name: openThread.value });
    toast.success(__("Sent to the dealer."));
  },
});

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
