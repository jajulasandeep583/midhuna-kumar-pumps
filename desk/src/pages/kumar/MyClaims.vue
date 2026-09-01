<template>
  <DealerList
    kind="claim"
    :title="__('Warranty Claims')"
    :add-label="__('New Claim')"
    new-route="KumarClaimNew"
    :empty-line="__('You have not claimed anything yet. A claim asks KUMAR to settle a failure under warranty.')"
    :search-hint="__('Claim number, serial or model')"
  />
</template>

<script setup lang="ts">
import DealerList from "./DealerList.vue";
import { __ } from "@/translation";
</script>
