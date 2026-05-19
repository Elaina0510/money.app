<template>
  <v-snackbar
    v-model="visible"
    :color="appStore.toast.color"
    location="top"
    :timeout="2500"
    rounded="pill"
  >
    <v-icon start class="mr-2">mdi-check-circle</v-icon>
    {{ appStore.toast.message }}
  </v-snackbar>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useAppStore } from '@/stores/useAppStore'

const appStore = useAppStore()
const visible = ref(false)

watch(() => appStore.toast.show, (val) => {
  if (val) {
    visible.value = true
    appStore.hideToast()
  }
})

watch(visible, (val) => {
  if (!val) {
    appStore.hideToast()
  }
})
</script>
