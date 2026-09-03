<template>
  <div>
    <label class="block text-xs font-medium text-ink-gray-7">{{ label || __("Photos, video or documents") }}</label>
    <div class="mt-1 flex flex-wrap items-center gap-2">
      <label class="inline-flex cursor-pointer items-center gap-1.5 rounded border bg-surface-white px-2.5 py-1.5 text-sm text-ink-gray-8 hover:bg-surface-gray-2">
        <LucidePaperclip class="size-4" />
        {{ __("Add files") }}
        <input class="hidden" type="file" multiple accept="image/*,video/*,application/pdf" @change="addFiles" />
      </label>
      <span class="text-xs text-ink-gray-5">{{ __("Up to {0} MB each", [String(MAX_MB)]) }}</span>
    </div>
    <ul v-if="modelValue.length" class="mt-2 flex flex-wrap gap-2">
      <li v-for="(f, i) in modelValue" :key="f.filename + i" class="flex items-center gap-2 rounded border bg-surface-gray-1 px-2 py-1 text-xs">
        <img v-if="f.preview" :src="f.preview" class="size-8 rounded object-cover" />
        <span class="max-w-[14rem] truncate text-ink-gray-8">{{ f.filename }}</span>
        <span class="text-ink-gray-5">{{ f.size }}</span>
        <button class="text-ink-gray-5 hover:text-red-600" :title="__('Remove')" @click="remove(i)">×</button>
      </li>
    </ul>
    <ErrorMessage v-if="error" class="mt-1" :message="error" />
  </div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { ErrorMessage } from "frappe-ui";
import LucidePaperclip from "~icons/lucide/paperclip";
import { ref } from "vue";

const props = defineProps<{ modelValue: any[]; label?: string }>();
const emit = defineEmits<{ (e: "update:modelValue", v: any[]): void }>();
const MAX_MB = 8;
const error = ref("");

function human(bytes: number) {
  return bytes > 1024 * 1024 ? (bytes / (1024 * 1024)).toFixed(1) + " MB" : Math.max(1, Math.round(bytes / 1024)) + " KB";
}
async function addFiles(e: Event) {
  error.value = "";
  const picked = Array.from((e.target as HTMLInputElement).files || []);
  const next = [...props.modelValue];
  for (const file of picked) {
    if (file.size > MAX_MB * 1024 * 1024) {
      error.value = __("{0} is too large. The limit is {1} MB.", [file.name, String(MAX_MB)]);
      continue;
    }
    const content = await new Promise<string>((resolve) => {
      const reader = new FileReader();
      // the API takes base64, so strip the data: prefix the reader adds
      reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
      reader.readAsDataURL(file);
    });
    next.push({ filename: file.name, content, size: human(file.size), preview: file.type.startsWith("image/") ? URL.createObjectURL(file) : "" });
  }
  (e.target as HTMLInputElement).value = "";
  emit("update:modelValue", next);
}
function remove(i: number) {
  const next = [...props.modelValue];
  next.splice(i, 1);
  emit("update:modelValue", next);
}
</script>
