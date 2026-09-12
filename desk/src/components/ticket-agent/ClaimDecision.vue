<template>
  <!-- The claim's workflow buttons and the dialog behind them. One component,
       used on the Claims desk card AND in the ticket header/panel, so deciding
       a claim looks and works the same wherever the user happens to be
       standing when they make up their mind. -->
  <div v-if="claim?.actions?.length" class="flex flex-wrap items-center gap-2">
    <Button
      v-for="a in claim.actions"
      :key="a.action"
      :size="size"
      :variant="a.action === 'Reject' ? 'subtle' : 'solid'"
      :theme="a.action === 'Reject' ? 'red' : 'blue'"
      :label="actionLabel(a.action)"
      @click="openAction(a)"
    />
  </div>

  <Dialog v-model="acting" :options="{ title: dialogTitle }">
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
        :loading="act.loading" :label="dialogTitle" @click="act.submit()" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { Button, Dialog, ErrorMessage, FormControl, createResource, toast } from "frappe-ui";
import { computed, ref } from "vue";

const props = withDefaults(
  defineProps<{
    claim: any; // { name, workflow_state, claim_amount, actions: [{action, next_state}] }
    size?: string;
  }>(),
  { size: "sm" }
);
const emit = defineEmits<{ (e: "done", result: any): void }>();

// the same words the Claims desk uses, so the two screens speak identically
function actionLabel(a: string) {
  return ({
    Review: __("Send for investigation"),
    Approve: __("Approve"),
    Reject: __("Reject"),
    Settle: __("Mark settled"),
  } as Record<string, string>)[a] || __(a);
}
function money(v: number) {
  return "₹" + Math.round(v || 0).toLocaleString("en-IN");
}

const acting = ref(false);
const pending = ref<any>(null);
const amount = ref<number | null>(null);
const remarks = ref("");
const dialogTitle = computed(() =>
  pending.value ? actionLabel(pending.value.action) + " " + (props.claim?.name || "") : ""
);

function openAction(a: any) {
  pending.value = a;
  amount.value = props.claim?.approved_amount || props.claim?.claim_amount || null;
  remarks.value = "";
  acting.value = true;
}

const act = createResource({
  url: "kumar_service.staff_api.claim_action",
  makeParams: () => ({
    name: props.claim?.name,
    action: pending.value?.action,
    approved_amount: pending.value?.action === "Approve" ? amount.value : undefined,
    remarks: remarks.value,
  }),
  onSuccess: (d: any) => {
    acting.value = false;
    toast.success(d?.message || __("Done"));
    emit("done", d);
  },
});
</script>
