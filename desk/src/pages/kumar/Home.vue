<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ __("Home") }}</div>
      </template>
    </LayoutHeader>

    <div class="px-5 py-6">
      <div class="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div v-for="s in stats" :key="s.label" class="rounded-lg border bg-surface-white p-4">
          <div class="text-xs text-ink-gray-5">{{ s.label }}</div>
          <div class="mt-1 text-2xl font-semibold tabular-nums text-ink-gray-9">
            {{ s.value }}
          </div>
        </div>
      </div>

      <div class="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-gray-4">
        {{ __("What do you need to do?") }}
      </div>
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <button
          v-for="a in actions"
          :key="a.name"
          class="flex items-start gap-3 rounded-lg border bg-surface-white p-4 text-left transition hover:border-outline-gray-3 hover:bg-surface-gray-1"
          @click="router.push({ name: a.name })"
        >
          <component :is="a.icon" class="mt-0.5 size-5 shrink-0 text-ink-gray-6" />
          <div>
            <div class="text-sm font-medium text-ink-gray-8">{{ a.label }}</div>
            <div class="mt-0.5 text-xs text-ink-gray-5">{{ a.hint }}</div>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { createResource } from "frappe-ui";
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";
import LucideFilePlus from "~icons/lucide/file-plus";
import LucideMessageSquare from "~icons/lucide/message-square";
import LucideShieldCheck from "~icons/lucide/shield-check";

const router = useRouter();
const summary = createResource({ url: "kumar_service.portal_api.my_summary", auto: true });

const stats = computed(() => [
  { label: __("Pumps you sold"), value: summary.data?.pumps ?? "-" },
  { label: __("In warranty"), value: summary.data?.in_warranty ?? "-" },
  { label: __("Expiring in 45 days"), value: summary.data?.expiring ?? "-" },
  { label: __("Open with KUMAR"), value: summary.data?.open_tickets ?? "-" },
]);

const actions = [
  {
    name: "KumarRegister",
    label: __("Register a Sale"),
    hint: __("The warranty starts from the registration"),
    icon: LucideFilePlus,
  },
  {
    name: "KumarComplaint",
    label: __("Raise a Complaint"),
    hint: __("We answer whether the visit is free"),
    icon: LucideMessageSquare,
  },
  {
    name: "KumarClaim",
    label: __("Warranty Claim"),
    hint: __("Ask KUMAR to settle a failure"),
    icon: LucideShieldCheck,
  },
];
</script>
