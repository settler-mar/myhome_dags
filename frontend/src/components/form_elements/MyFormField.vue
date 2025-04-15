<template>
  <div>
    <!-- Цвет -->
    <v-color-picker
      v-if="field.name.toLowerCase() === 'color'"
      v-model="model"
      hide-inputs
      mode="hexa"
      :swatches="color_swatches"
      flat
      show-swatches
      :label="field.title || field.name"
      hide-details
      swatches-max-height="400px"
    />

    <!-- Иконка -->
    <v-combobox
      v-else-if="field.name.toLowerCase() === 'icon'"
      v-model="model"
      :label="field.title || field.name"
      :items="iconOptions"
      clearable
      append-inner-icon="mdi-star"
      hide-details
    >
      <template v-slot:item="{ item }">
        <v-icon left>{{ item }}</v-icon>
        <span>{{ item }}</span>
      </template>
      <template v-slot:selection="{ item }">
        <v-icon>{{ item }}</v-icon>
        <span class="ml-1">{{ item }}</span>
      </template>
    </v-combobox>

    <!-- Булево -->
    <v-switch
      v-else-if="isBoolean"
      v-model="model"
      :label="field.title || field.name"
      hide-details
    />

    <!-- Многострочный -->
    <v-textarea
      v-else-if="isTextarea"
      v-model="model"
      :label="field.title || field.name"
      rows="3"
      hide-details
    />

    <!-- Число -->
    <v-text-field
      v-else-if="isNumber"
      v-model.number="model"
      :label="field.title || field.name"
      type="number"
      hide-details
    />

    <!-- По умолчанию -->
    <v-text-field
      v-else
      v-model="model"
      :label="field.title || field.name"
      hide-details
    />
  </div>
</template>

<script setup>
import {computed} from 'vue'

const props = defineProps({
  field: Object,
  modelValue: [String, Number, Boolean, null],
})

const emit = defineEmits(['update:modelValue'])

const color_swatches = [
  ['#F44336', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#03A9F4'],
  ['#00BCD4', '#009688', '#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107'],
  ['#FF9800', '#FF5722', '#795548', '#9E9E9E', '#607D8B', '#D32F2F', '#C2185B'],
  ['#7B1FA2', '#512DA8', '#303F9F', '#1976D2', '#0288D1', '#0097A7', '#00796B'],
  ['#388E3C', '#689F38', '#AFB42B', '#FBC02D', '#FFA000', '#F57C00', '#E64A19']
]

const model = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const type = (props.field?.type || '').toLowerCase()

const isBoolean = type.includes('bool')
const isNumber = type.includes('int') || type.includes('numeric')
const isTextarea = type.includes('text') && !type.includes('varchar')

const iconOptions = [
  'mdi-home', 'mdi-map-marker', 'mdi-account', 'mdi-camera', 'mdi-bell',
  'mdi-calendar', 'mdi-chart-bar', 'mdi-star', 'mdi-cog', 'mdi-heart',
  'mdi-folder', 'mdi-lightbulb', 'mdi-lock', 'mdi-tag',
]
</script>

<style scoped>
.v-combobox .v-icon {
  margin-right: 6px;
}
</style>
