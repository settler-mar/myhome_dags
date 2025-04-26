<template>
  <v-autocomplete
    v-model="model"
    :items="filteredIcons"
    item-title="label_output"
    item-value="value"
    :label="label"
    return-object
    clearable
    chips
    density="comfortable"
    :disabled="disabled"
    menu-icon=""
    class="icon-select"
    @update:menu="menuOpen = $event"
  >
    <!-- Выбранное значение -->
    <template v-slot:chip="{ props, item }">
      <v-chip>
        <m-icon
          :code="item.value.split('/').pop()"
          :folder="item.value.includes('/') ? item.value.split('/')[0] : undefined"
          :type="item.raw.defined ? 'font' : 'svg'"
          size="20"
          class="me-2"
        />
        <span v-if="item.raw.defined">{{ item.raw.name }}</span>
        <span v-else>{{ item.raw.label }}</span>
      </v-chip>
    </template>

    <!-- Рендер выпадающего списка -->
    <template #item="{ item, props }">
      <v-list-item v-bind="props">
        <template #prepend>
          <m-icon
            :code="item.value.split('/').pop()"
            :folder="item.value.includes('/') ? item.value.split('/')[0] : undefined"
            :type="item.raw.defined ? 'font' : 'svg'"
            size="20"
            class="me-2"
          />
        </template>
      </v-list-item>
    </template>

    <!-- Расширенный контент сверху -->
    <template #prepend-item>
      <div class="icon-select-prepend px-4 pt-2 pb-1" v-if="menuOpen">
        <v-checkbox
          v-model="showAll"
          label="Показать все иконки"
          density="compact"
          hide-details
        />
        <v-select
          v-if="showAll"
          v-model="selectedFolder"
          :items="availableFolders"
          label="Папка"
          clearable
          density="compact"
          hide-details
        />
        <v-divider class="mt-2 mb-1"/>
      </div>
    </template>
  </v-autocomplete>
</template>

<script setup>
import {ref, watch, computed, onMounted} from 'vue'
import {useIconStore} from '@/store/iconStore'

const props = defineProps({
  modelValue: [String, null],
  is_null: {type: Boolean, default: true},
  label: {type: String, default: 'Выберите иконку'},
  disabled: Boolean,
})

const emit = defineEmits(['update:modelValue'])

const store = useIconStore()
const model = ref(null)
const showAll = ref(false)
const selectedFolder = ref(null)
const menuOpen = ref(false)

const availableFolders = computed(() => {
  const folders = new Set()
  store.icons.forEach(icon => {
    if (icon.folder) folders.add(icon.folder)
  })
  return Array.from(folders).sort()
})

const filteredIcons = computed(() => {
  let icons = store.icons

  if (!showAll.value) {
    icons = icons.filter(i => i.defined)
  } else if (selectedFolder.value) {
    icons = icons.filter(i => i.folder === selectedFolder.value)
  }

  return icons.map(i => ({
    label: i.folder ? `${i.folder}/${i.name}` : i.name,
    value: i.folder ? `${i.folder}/${i.name}` : i.name,
    defined: i.defined,
    name: i.name,
    label_output: i.defined || !i.folder ? i.name : `${i.folder}/${i.name}`,
  }))
})

watch(() => props.modelValue, val => {
  const match = filteredIcons.value.find(i => i.value === val)
  model.value = match || null
}, {immediate: true})

watch(model, val => {
  if (val === null || !val) {
    emit('update:modelValue', props.is_null ? null : '')
    return
  }
  emit('update:modelValue', val ? val.value : (props.is_null ? null : ''))
})

onMounted(async () => {
  await store.loadIconsWithMeta()
  await store.loadConfig()
})
</script>

<style scoped>
.icon-select-prepend {
  position: sticky;
  top: 0;
  background: white;
  z-index: 2;
}
</style>
