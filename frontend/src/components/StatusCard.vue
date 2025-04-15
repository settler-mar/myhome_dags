<template>
  <div class="bg-white shadow rounded p-4 mb-4 border border-gray-200">
    <div class="flex items-center justify-between mb-2">
      <h3 class="text-lg font-semibold text-gray-700">
        <v-icon v-if="icon" class="mr-2" :icon="icon" size="20" />
        {{ title }}
      </h3>
      <span v-if="badge" class="text-xs font-medium bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
        {{ badge }}
      </span>
    </div>
    <div class="text-sm text-gray-800 whitespace-pre-wrap break-words leading-relaxed">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { VIcon } from 'vuetify/components'

defineProps<{
  title: string
  icon?: string
  badge?: string
}>()
</script>

<style scoped>
</style>
