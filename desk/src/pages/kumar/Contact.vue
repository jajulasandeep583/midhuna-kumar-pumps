<template>
  <div>
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-semibold text-ink-gray-9">{{ __("Contact KUMAR") }}</div>
      </template>
    </LayoutHeader>

    <div class="px-5 py-6">
      <div v-if="contacts.loading" class="text-sm text-ink-gray-5">{{ __("Loading...") }}</div>
      <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div v-for="c in contacts.data || []" :key="c.role + c.dealer_name" class="rounded-lg border bg-surface-white p-4">
          <div class="text-[10px] font-semibold uppercase tracking-wider text-ink-gray-5">
            {{ c.role }}
          </div>
          <div class="mt-1 text-sm font-medium text-ink-gray-9">{{ c.dealer_name }}</div>
          <p v-if="c.contact_person" class="mt-0.5 text-xs text-ink-gray-6">
            {{ c.contact_person }}
          </p>
          <p v-if="c.city" class="mt-1 text-xs text-ink-gray-5">
            {{ [c.city, c.state].filter(Boolean).join(", ") }}
          </p>
          <a
            v-if="c.mobile_no"
            class="mt-3 block text-sm font-medium tabular-nums text-ink-blue-3"
            :href="`tel:${c.mobile_no}`"
            >{{ c.mobile_no }}</a
          >
          <a
            v-if="c.landline"
            class="mt-0.5 block text-sm tabular-nums text-ink-blue-3"
            :href="`tel:${c.landline}`"
            >{{ c.landline }}</a
          >
          <div v-if="c.email_id" class="mt-1 text-xs text-ink-gray-5">{{ c.email_id }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { createResource } from "frappe-ui";
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";

const contacts = createResource({ url: "kumar_service.portal_api.my_contacts", auto: true });
</script>
