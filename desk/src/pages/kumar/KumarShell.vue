<template>
  <!-- One frame for every dealer page, so the rail does not rebuild between
       routes and the page keeps its scroll. -->
  <div class="flex h-screen w-screen overflow-hidden">
    <KumarSidebar />
    <div class="flex min-w-0 flex-1 flex-col overflow-auto">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import KumarSidebar from "./KumarSidebar.vue";
</script>
