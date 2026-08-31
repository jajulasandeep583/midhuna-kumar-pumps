<template>
  <!-- The dealer's own work, alongside the ticket list rather than on a
       different website. One login, one place. -->
  <div class="flex items-center gap-1 overflow-x-auto border-b bg-surface-white px-5 py-2">
    <router-link
      v-for="item in items"
      :key="item.name"
      :to="{ name: item.name }"
      class="whitespace-nowrap rounded px-3 py-1.5 text-sm font-medium transition"
      :class="
        route.name === item.name
          ? 'bg-surface-gray-3 text-ink-gray-9'
          : 'text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-8'
      "
    >
      {{ item.label }}
    </router-link>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { __ } from "@/translation";

const route = useRoute();

const items = computed(() => [
  { name: "TicketsCustomer", label: __("My Tickets") },
  { name: "KumarComplaint", label: __("Raise a Complaint") },
  { name: "KumarPumps", label: __("My Pumps") },
]);
</script>
