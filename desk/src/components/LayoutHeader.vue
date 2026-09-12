<template>
  <Teleport to="#app-header" v-if="showHeader">
    <slot>
      <!-- min-height, not height: the ticket header stacks breadcrumbs, a
           wrapping chip row and the channel line under one slot, and a fixed
           42px scissored the top line off with no way to scroll it back.
           Single-line headers still sit at exactly 42px. -->
      <header
        class="flex min-h-[42px] items-center justify-between gap-3 py-1 mx-4 md:ms-5 md:me-0"
      >
        <div class="flex items-center gap-2 min-w-0 flex-1">
          <slot name="left-header" />
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <slot name="right-header" class="flex items-center gap-2" />
        </div>
      </header>
    </slot>
  </Teleport>
</template>
<script setup>
import { nextTick, ref } from "vue";
const showHeader = ref(false);

nextTick(() => {
  showHeader.value = true;
});
</script>
