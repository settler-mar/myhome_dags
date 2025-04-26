<template>
  <v-dialog v-model="dialog" max-width="800">
    {{ permissions_computed }}
    <v-card>
      <v-card-title class="d-flex justify-space-between">
        {{ form.id ? 'Изменить' : 'Добавить' }} {{ table }}
        <v-btn icon @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-progress-linear
          v-if="onload"
          color="deep-purple-accent-4"
          height="6"
          indeterminate
          rounded
        />
        <div v-if="descriptionText" class="mb-4 text-grey text-body-2">
          {{ descriptionText }}
        </div>
        <v-container>
          <v-row>
            <v-col cols="12" sm="6" v-for="field in mergedFields" :key="field.name">
              <MyFormField
                v-model="form[field.name]"
                :field="field"
                :required="requiredFields.includes(field.name)"
                :readonly="onload || field.readonly || (!permissions_computed  && !['name', 'description','location_id'].includes(field.name))"
              />
            </v-col>
          </v-row>
          <v-row v-if="onlyShowFieldsComputed.length">
            <v-col cols="12" sm="6" v-for="field in onlyShowFieldsComputed" :key="field.name">
              <MyFormField
                v-model="form[field.name]"
                :field="field"
                :readonly="true"
              />
            </v-col>
          </v-row>
        </v-container>
        <v-progress-linear
          v-if="onload"
          color="deep-purple-accent-4"
          height="6"
          indeterminate
          rounded
        />
      </v-card-text>

      <v-card-actions>
        <v-spacer/>
        <v-btn text @click="dialog = false">Отмена</v-btn>
        <v-btn color="primary" @click="save" :disabled="onload">Сохранить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import {ref, computed, watch} from 'vue'
import {useTableStore} from '@/store/tables'
import {useConnectionsStore} from '@/store/connectionsStore'
import useMessageStore from '@/store/messages'
import MyFormField from '@/components/form_elements/MyFormField.vue'
import {objectToFlat} from '@/utils/array'

const messageStore = useMessageStore()

const props = defineProps({
  show: Boolean,
  table: {type: String, required: true},
  item: {type: Object, default: () => ({})},
  parentId: {type: [String, Number], default: null},
  custom_params: {type: Object, default: () => ({})},
  permissions: {type: Object, default: () => ({})}
})

const emit = defineEmits(['save', 'update:show'])
const form = ref({})
const onload = ref(false)

const tableStore = useTableStore()
const connectionStore = useConnectionsStore()

const structure = computed(() => tableStore.tables[props.table]?.structure || [])

const parentField = computed(() => {
  if (props.table === 'devices') return 'connection_id'
  if (props.table === 'ports') return 'device_id'
  return null
})

const permissions_computed = computed(() => {
  if (!props.permissions || !form.value.id) return true
  return {
    'devices': props.permissions.edit_device,
    'port': props.permissions.edit_port,
  }[props.table]
})

const excludeFields = ['id', 'params', 'created_at', 'created_by', 'updated_at', 'updated_by']

const onlyShowFields = ['created_at', 'created_by', 'updated_at', 'updated_by']

const structureToShow = computed(() => {
  return structure.value.filter(field => {
    if (excludeFields.includes(field.name)) return false
    if (field.name === parentField.value) return false
    return true
  })
})

const mergedFields = computed(() => {
  const tableFields = structureToShow.value

  let customFields = [...tableFields]
  let params = {...props.custom_params}
  for (const index in tableFields) {
    const field = tableFields[index]
    if (field.name in params) {
      customFields[index] = {...field, ...params[field.name]}
      delete params[field.name]
    }
  }
  for (const key in params) {
    customFields.push({
      name: key,
      ...params[key]
    })
  }

  return customFields
})

const formResult = computed(() => {
  let result = {}
  for (let key in form.value) {
    if (onlyShowFields.includes(key)) continue

    let value = form.value[key]
    if (excludeFields.includes(key) || key === parentField.value) {
      value = props.item[key]
    }

    key = key.split('.')
    if (!table_columns.value.includes(key[0])) continue
    if (key.length > 1) {
      result[key[0]] = result[key[0]] || {}
      result[key[0]][key[1]] = value
    } else {
      if (result[key[0]]) continue
      result[key[0]] = value
    }
  }

  return result
})

const table_columns = computed(() => {
  return structure.value.map(field => {
    return field.name
  })
})

const onlyShowFieldsComputed = computed(() => {
  return structure.value.filter(field => onlyShowFields.includes(field.name))
})

const requiredFields = computed(() => {
  return mergedFields.value.filter(field => !onlyShowFields.includes(field.name) && (field.required || !field.nullable))
})


const descriptionText = computed(() => {
  if (props.table === 'devices') {
    const conn = connectionStore.available.find(c => c.type === props.item?.type)
    return conn?.description || null
  }
  return null
})

const dialog = computed({
  get: () => props.show,
  set: (val) => emit('update:show', val)
})

watch(() => props.item, (val) => {
  form.value = {...objectToFlat(val)}
  if (!form.value.params) form.value.params = {}
  if (parentField.value && props.parentId !== null) {
    form.value[parentField.value] = props.parentId
  }

  // initialize custom_params if not set
  for (const key in props.custom_params) {
    if (!(key in form.value)) {
      form.value[key] = props.custom_params[key].default ?? null
    }
  }
}, {immediate: true})

function save() {
  let has_no_required = false
  for (const field of requiredFields.value) {
    if (form.value[field.name]) continue
    if (field.type === 'bool' && form.value[field.name] === false) continue
    has_no_required = true
    messageStore.addMessage({
      text: `Поле ${field.description || field.name} обязательно для заполнения`,
      type: 'error'
    })
  }

  if (has_no_required) return;
  onload.value = true

  let dataToSend = {
    ...formResult.value
  }
  tableStore.saveItem(props.table, dataToSend).then(success => {
    onload.value = false
    if (success) {
      emit('save')
      tableStore.reloadTableData(props.table)
    }
  })
}
</script>
