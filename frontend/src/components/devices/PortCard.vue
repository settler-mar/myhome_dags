<template>
  <v-card class="pa-2" elevation="0" outlined>
    <v-row align="center">
      <v-col cols="9">
        <div class="text-subtitle-2">🔌 {{ port.name }}</div>
        <div class="text-caption text-grey">{{ port.description || 'Порт без описания' }}</div>
        <div v-if="port.location" class="text-caption mt-1">📍 {{ port.location }}</div>
      </v-col>
      <v-col cols="3" class="text-right">
        <v-btn icon size="small" v-if="!readonly" @click="$emit('edit', port)">
          <v-icon>mdi-pencil</v-icon>
        </v-btn>
      </v-col>
    </v-row>
  </v-card>
</template>

<script setup>
const props = defineProps({
  port: Object,
  readonly: Boolean,
})
</script>
