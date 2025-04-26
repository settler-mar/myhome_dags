<template>
  <div v-if="only_value">
    <component :is="viewContent" v-if="typeof viewContent !== 'string'"/>
    <span v-else>{{ viewContent }}</span>
  </div>
  <div v-else>
    <!-- Цвет -->
    <v-color-picker
      v-if="(field?.name || '').toLowerCase() === 'color'"
      v-model="model"
      hide-inputs
      mode="hexa"
      :swatches="color_swatches"
      flat
      show-swatches
      :label="label"
      hide-details
      swatches-max-height="400px"
      :disabled="readonly"
    />

    <!-- Иконка -->
    <iconSelect
      v-else-if="(field?.name || '').toLowerCase() === 'icon'"
      v-model="model"
      :label="label"
      hide-details
      :disabled="readonly"
    />


    <!-- Булево -->
    <v-switch
      :disabled="readonly"
      v-else-if="isBoolean"
      v-model="model"
      :label="label"
      hide-details
    />

    <!-- list / select-->
    <v-select
      v-else-if="typeEl==='select'"
      :items="options"
      :label="label"
      v-model="model"
      hide-details
      :disabled="readonly"
      :clearable="clearable"
    ></v-select>

    <!-- Многострочный -->
    <v-textarea
      v-else-if="isTextarea"
      v-model="model"
      :label="label"
      rows="3"
      hide-details
      :disabled="readonly"
    />

    <!-- Число -->
    <v-text-field
      v-else-if="isNumber"
      v-model.number="model"
      :label="label"
      type="number"
      hide-details
      :disabled="readonly"
    />

    <!-- По умолчанию -->
    <v-text-field
      v-else
      v-model="model"
      :label="label"
      hide-details
      :disabled="readonly"
    />
  </div>
</template>

<script setup>
import {computed} from 'vue'
import {useTableStore} from '@/store/tables'
import iconSelect from '@/components/form_elements/IconSelect.vue'

const tables = useTableStore()

const props = defineProps({
  field: Object,
  modelValue: [String, Number, Boolean, null],
  readonly: {
    'type': Boolean,
    'default': false,
  },
  only_value: {
    'type': Boolean,
    'default': false,
  }
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

const label = props.field?.title || props.field?.description || props.field?.element?.name || props.field?.name
const clearable = props.field?.element?.nullable || props.field?.nullable || false
const iconOptions = [
  'mdi-home', 'mdi-map-marker', 'mdi-account', 'mdi-camera', 'mdi-bell',
  'mdi-calendar', 'mdi-chart-bar', 'mdi-star', 'mdi-cog', 'mdi-heart',
  'mdi-folder', 'mdi-lightbulb', 'mdi-lock', 'mdi-tag',
]

const typeEl = computed(() => {
  if (props.field?.type === 'list' || props.field?.type === 'select') {
    return 'select'
  }
  if (props.field?.element?.type === 'alias') {
    return 'select'
  }
  if (props.field?.type === 'icon') {
    return 'icon'
  }
  if (props.field?.type === 'color') {
    return 'color'
  }
  if (props.field?.type === 'bool') {
    return 'bool'
  }
  if (props.field?.type === 'text' && !isTextarea) {
    return 'text'
  }
  return type
})

const options = computed(() => {
  if (props.field?.element?.type === 'alias') {
    tables.loadTableData(props.field?.element?.table)
    return tables.tables[props.field?.element?.table]?.items.map((item) => {
      const template = props.field?.element?.template || '{name}'
      const value = template.replace(/{([^}]+)}/g, (_, key) => item[key] || '')
      return {
        title: value,
        value: item[props.field?.element?.key],
      }
    })
  }

  if (!['list', 'select'].includes(props.field?.type)) {
    return []
  }
  const values = props.field?.values || props.field?.options || []
  let result = []
  if (Array.isArray(values)) {
    result = values.map((item) => ({
      title: item,
      value: item,
    }))
  } else if (typeof values === 'object') {
    result = Object.entries(values).map(([key, value]) => ({
      title: value,
      value: key,
    }))
  }
  return result
})

const viewText = computed(() => {
  if (typeEl.value === 'select') {
    const selected = options.value.find(o => o.value === model.value)
    return selected ? selected.title : model.value
  }
  if (typeof model.value === 'boolean') {
    return model.value ? 'Да' : 'Нет'
  }
  return model.value ?? ''
})

const viewContent = computed(() => {
  if (typeEl.value === 'color' && model.value) {
    return h('div', {
      style: {
        backgroundColor: model.value,
        width: '40px',
        height: '20px',
        borderRadius: '4px',
        border: '1px solid #ccc',
        display: 'inline-block',
      }
    })
  }
  if (typeEl.value === 'icon' && model.value) {
    return h('v-icon', {}, model.value)
  }
  return viewText.value
})
</script>

<style scoped>
.v-combobox .v-icon {
  margin-right: 6px;
}

.color-box {
  width: 40px;
  height: 20px;
  border-radius: 4px;
  border: 1px solid #ccc;
  display: inline-block;
}
</style>
