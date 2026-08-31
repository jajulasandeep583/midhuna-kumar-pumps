<template>
  <!-- Everything a dealer does, in one rail. The portal used to be seven tabs
       on a separate website; this is the same seven, in the desk, next to the
       ticket thread they all end up in. -->
  <div
    class="flex h-full shrink-0 flex-col border-r bg-surface-menu-bar transition-all"
    :class="collapsed ? 'w-14' : 'w-56'"
  >
    <div class="flex items-center gap-2 px-3 py-3">
      <img :src="logo" alt="" class="size-7 shrink-0" />
      <div v-if="!collapsed" class="min-w-0">
        <div class="truncate text-sm font-semibold text-ink-gray-9">KUMAR</div>
        <div class="truncate text-[10px] uppercase tracking-wider text-ink-gray-5">
          {{ __("Pumps Desk") }}
        </div>
      </div>
    </div>

    <div v-if="!collapsed && dealerName" class="px-3 pb-2">
      <div class="truncate text-xs text-ink-gray-6">{{ dealerName }}</div>
    </div>

    <nav class="flex-1 overflow-y-auto px-2 pb-3">
      <template v-for="group in groups" :key="group.title">
        <div
          v-if="!collapsed"
          class="px-2 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-wider text-ink-gray-4"
        >
          {{ group.title }}
        </div>
        <router-link
          v-for="item in group.items"
          :key="item.name"
          :to="{ name: item.name }"
          class="mb-0.5 flex items-center gap-2.5 rounded px-2 py-1.5 text-sm transition"
          :class="
            isActive(item)
              ? 'bg-surface-selected font-medium text-ink-gray-9'
              : 'text-ink-gray-7 hover:bg-surface-gray-2'
          "
          :title="collapsed ? item.label : undefined"
        >
          <component :is="item.icon" class="size-4 shrink-0" />
          <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
          <span
            v-if="!collapsed && item.count"
            class="ml-auto rounded bg-surface-gray-3 px-1.5 text-xs tabular-nums text-ink-gray-7"
          >
            {{ item.count }}
          </span>
        </router-link>
      </template>
    </nav>

    <button
      class="border-t px-3 py-2 text-left text-xs text-ink-gray-5 hover:bg-surface-gray-2"
      @click="collapsed = !collapsed"
    >
      {{ collapsed ? "»" : "« " + __("Collapse") }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { createResource } from "frappe-ui";
import { __ } from "@/translation";
import LucideHome from "~icons/lucide/home";
import LucideFilePlus from "~icons/lucide/file-plus";
import LucideMessageSquare from "~icons/lucide/message-square";
import LucideShieldCheck from "~icons/lucide/shield-check";
import LucideList from "~icons/lucide/list";
import LucideTicket from "~icons/lucide/ticket";
import LucidePhone from "~icons/lucide/phone";

// a runtime path, not a bundled asset: vite would try to resolve an absolute
// /assets url as a module and fail the build
const logo = "/assets/kumar_service/images/kumar-mark.svg";
const route = useRoute();
const collapsed = ref(false);

const summary = createResource({ url: "kumar_service.portal_api.my_summary", auto: true });
const dealerName = computed(() => summary.data?.dealer_name || "");

function isActive(item: any) {
  return route.name === item.name;
}

const groups = computed(() => [
  {
    title: __("Overview"),
    items: [{ name: "KumarHome", label: __("Home"), icon: LucideHome }],
  },
  {
    title: __("Sell"),
    items: [
      { name: "KumarRegister", label: __("Register a Sale"), icon: LucideFilePlus },
      {
        name: "KumarPumps",
        label: __("What I Sold"),
        icon: LucideList,
        count: summary.data?.pumps,
      },
    ],
  },
  {
    title: __("Service"),
    items: [
      { name: "KumarComplaint", label: __("Raise a Complaint"), icon: LucideMessageSquare },
      { name: "KumarClaim", label: __("Warranty Claim"), icon: LucideShieldCheck },
      {
        name: "TicketsCustomer",
        label: __("My Tickets"),
        icon: LucideTicket,
        count: summary.data?.open_tickets,
      },
    ],
  },
  {
    title: __("Help"),
    items: [{ name: "KumarContact", label: __("Contact KUMAR"), icon: LucidePhone }],
  },
]);
</script>
