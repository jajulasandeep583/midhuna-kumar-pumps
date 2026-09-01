<template>
  <DealerList
    kind="complaint"
    :title="__('My Requests')"
    :add-label="__('New Request')"
    new-route="KumarComplaintNew"
    :empty-line="__('You have not raised anything yet. A request is how you ask KUMAR for a visit, a part or an installation.')"
    :search-hint="__('Request number, serial or model')"
  />
</template>

<script setup lang="ts">
import DealerList from "./DealerList.vue";
import { __ } from "@/translation";
</script>
