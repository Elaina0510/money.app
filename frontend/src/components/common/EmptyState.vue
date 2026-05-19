<template>
  <div class="empty-state text-center pa-8">
    <v-icon :icon="icon" size="64" color="grey-lighten-1" class="mb-4" />
    <p class="text-grey text-body-1 mb-2">{{ title }}</p>
    <p class="text-grey-lighten-1 text-caption">{{ subtitle }}</p>
    <v-btn v-if="actionText" :color="actionColor" variant="tonal" class="mt-4" @click="$emit('action')">
      <v-icon start :icon="actionIcon" />
      {{ actionText }}
    </v-btn>
  </div>
</template>

<script setup>
defineProps({
  icon: { type: String, default: 'mdi-inbox-outline' },
  title: { type: String, default: '暂无数据' },
  subtitle: { type: String, default: '这里还没有内容' },
  actionText: { type: String, default: '' },
  actionIcon: { type: String, default: 'mdi-plus' },
  actionColor: { type: String, default: 'primary' },
})

defineEmits(['action'])
</script>
