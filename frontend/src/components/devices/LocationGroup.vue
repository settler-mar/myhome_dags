<template>
  <v-card class="mb-4" elevation="2">
    <v-card-title>
      📍 {{ location || 'Без локации' }}
    </v-card-title>
    <v-card-text>
      <v-row>
        <v-col cols="12" sm="6" md="4" v-for="device in devices" :key="device.id">
          <DeviceCard :device="device" :readonly="readonly" />
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup>
import DeviceCard from '@/components/devices/DeviceCard.vue'

const props = defineProps({
  location: String,
  devices: Array,
  readonly: Boolean,
})
</script>
