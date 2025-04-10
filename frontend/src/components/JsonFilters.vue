<template>
  <table class="json-filter-container">
    <tr>
      <td class="title" colspan="3">Фильтры по JSON</td>
      <td width="30"></td>
      <td>
        <v-btn icon size="small" @click="addFilter" density="compact">
          <v-icon>mdi-plus</v-icon>
        </v-btn>
      </td>
    </tr>
    <tr
      v-for="(filter, index) in localFilters"
      :key="index"
    >
      <td>
        <v-checkbox v-model="filter.active" hide-details color="info"></v-checkbox>
      </td>
      <td>
        <!-- Ключ -->
        <v-select
          :items="availableKeysFiltered"
          v-model="filter.key"
          label="Поле"
          density="compact"
          hide-details
          class="filter-input key"
        />
      </td>
      <td>
        <!-- Оператор -->
        <v-select
          v-if="filterType(filter.key) === 'string'"
          v-model="filter.mode"
          :items="['contains', 'startsWith', 'endsWith', '!=','=']"
          label="Условие"
          density="compact"
          hide-details
          class="filter-input mode"
        />
        <v-select
          v-else-if="filterType(filter.key) === 'number'"
          v-model="filter.mode"
          :items="['=', '!=', '>', '>=', '<', '<=']"
          label="Условие"
          density="compact"
          hide-details
          class="filter-input mode"
        />
      </td>
      <td>
        <!-- Значение -->
        <v-select
          v-if="shouldUseSelect(filter)"
          v-model="filter.value"
          :items="Array.from(values[filter.key])"
          label="Значение"
          density="compact"
          hide-details
          class="filter-input value"
        />

        <v-select
          v-else-if="filterType(filter.key) === 'boolean'"
          v-model="filter.value"
          :items="[true, false]"
          label="Значение"
          density="compact"
          hide-details
          class="filter-input value"
        />

        <v-text-field
          v-else
          v-model="filter.value"
          label="Значение"
          density="compact"
          hide-details
          class="filter-input value"
        />
      </td>
      <td></td>
      <td>
        <!-- Удалить -->
        <v-btn
          icon
          size="small"
          @click="removeFilter(index)"
          density="compact"
          class="ml-auto"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </td>
    </tr>
  </table>
</template>

<script setup>
import {ref, watch, computed} from 'vue'

const props = defineProps({
  availableKeys: {type: Array, required: true},
  types: {type: Object, required: true},
  values: {type: Object, required: true},
  filters: {type: Array, required: true}
})

const emit = defineEmits(['update'])

const localFilters = ref([])

function filterType(key) {
  return props.types[key] || 'string'
}

const availableKeysFiltered = computed(() =>
  props.availableKeys.filter(key => {
    const uniqueCount = props.values[key]?.size || 0
    const alreadyUsed = localFilters.value.some(f => f.key === key)
    return uniqueCount > 1 && !alreadyUsed
  })
)

function addFilter() {
  const nextKey = availableKeysFiltered.value[0]
  if (nextKey) {
    const type = filterType(nextKey)
    localFilters.value.push({
      key: nextKey,
      mode: type === 'number' ? '=' : 'contains',
      value: type === 'boolean' ? false : '',
      active: false
    })
    emit('update', [...localFilters.value])
  }
}

function removeFilter(index) {
  localFilters.value.splice(index, 1)
  emit('update', [...localFilters.value])
}

function shouldUseSelect(filter) {
  const valSet = props.values[filter.key]
  const isEqualsOp = ['=', '!='].includes(filter.mode)
  return filterType(filter.key) === 'string' && valSet && valSet.size <= 10 && isEqualsOp
}

watch(
  () => props.filters,
  (newFilters) => {
    localFilters.value = JSON.parse(JSON.stringify(newFilters))
  },
  {immediate: true, deep: true}
)

const previousFilters = ref(JSON.stringify(props.filters))
watch(localFilters, () => {
  const currentFilters = JSON.stringify(localFilters.value)
  if (currentFilters === previousFilters.value) return
  previousFilters.value = currentFilters
  emit('update', [...localFilters.value])
}, {deep: true})
</script>

<style scoped>
.json-filter-container {
  border: 1px solid #ccc;
  padding: 1rem;
  border-radius: 6px;
  background-color: #fff;
  max-width: 100%;
  min-width: 300px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.title {
  font-weight: 600;
  font-size: 0.95rem;
  color: #333;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.filter-input {
  width: 100%;
  min-width: 80px;
}

.filter-input.key {
  max-width: 180px;
}

.filter-input.mode {
  max-width: 200px;
}

.filter-input.value {
  width: 400px;
}
</style>
