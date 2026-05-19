<template>
  <div class="loading-spinner text-center pa-6">
    <v-progress-circular
      :size="size"
      :width="width"
      color="primary"
      indeterminate
    />
    <p v-if="text" class="text-grey text-caption mt-3">{{ text }}</p>
  </div>
</template>

<script setup>
defineProps({
  size: { type: Number, default: 40 },
  width: { type: Number, default: 4 },
  text: { type: String, default: '加载中...' },
})
</script>
