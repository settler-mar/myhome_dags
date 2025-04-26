<template>
  <v-dialog v-model="modelValue" max-width="800">
    <v-card>
      <v-card-title class="d-flex justify-space-between">
        {{ form.id ? 'Изменить' : 'Добавить' }} подключение
        <v-btn icon @click="emit('cancel')">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text>
        <v-row>
          <v-col cols="12" sm="6">
            <v-text-field v-model="form.name" label="Название" required/>
          </v-col>

          <v-col cols="12" sm="6">
            <v-select
              v-model="form.type"
              :items="types"
              item-title="name"
              item-value="code"
              label="Тип подключения"
              :disabled="!!form.id"
              required
              @update:modelValue="loadParams"
            />
          </v-col>
        </v-row>

        <v-row v-if="paramDefs">
          <v-col v-for="field in paramDefs" :key="field.name" cols="12" sm="6">
            <MyFormField
              v-if="connection_columns.includes(field.name)"
              v-model="form[field.name]"
              :field="field"
              :readonly="onload || (field.readonly  && !['name', 'description'].includes(field.name))"
            />
            <MyFormField
              v-else
              v-model="form.params[field.name]"
              :field="field"
              :readonly="onload || (field.readonly  && !['name', 'description'].includes(field.name))"
            />
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-actions>
        <v-spacer/>
        <v-btn color="grey" @click="emit('cancel')">Отмена</v-btn>
        <v-btn color="primary" @click="save">Сохранить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import {computed, reactive, watch} from 'vue'
import {useConnectionsStore} from '@/store/connectionsStore'
import {useTableStore} from '@/store/tables'
import MyFormField from '@/components/form_elements/MyFormField.vue'

const props = defineProps({
  connection: Object
})
const emit = defineEmits(['update:modelValue', 'cancel', 'save'])

const tableStore = useTableStore()
const connectionStore = useConnectionsStore()
const modelValue = ref(false)
const onload = ref(false)

const form = reactive({
  id: null,
  name: '',
  type: '',
  params: {}
})

const types = computed(() => {
  return connectionStore.available || []
})

const paramDefs = computed(() => {
  const def = connectionStore.available.find(c => c.code === form.type)
  // convert {key: {type: 'string', default: ''}} to {key: {type: 'string', default: ''}}
  // to [{type: 'string', default: '', name: 'key'}, {type: 'string', default: '', name: 'key'}]
  if (def?.params) {
    return Object.entries(def.params).map(([key, value]) => ({
      ...value,
      name: key
    }))
  }
  // if no params, return null
  return null
})

function loadParams() {
  const def = connectionStore.available.find(c => c.code === form.type)
  if (!def) return
  form.params = {}
  for (const [key, val] of Object.entries(def.params || {})) {
    form.params[key] = val.default ?? ''
  }
}

function save() {
  tableStore.saveItem('connections', form).then(success => {
    if (success) emit('save')
  })
}

const connection_columns = computed(() => {
  const struct = tableStore.tables['connections']?.structure || []
  return struct.map(field => field.name).filter(name => name[0] !== '_')
})

watch(
  () => props.connection,
  (conn) => {
    conn = conn || {}
    form.id = null
    form.name = ''
    form.type = ''

    console.log('conn', conn)
    for (const key of connection_columns.value) {
      if (conn[key] === undefined) continue
      if (key === 'params') {
        form.params = {...conn[key]}
        continue
      }
      form[key] = conn[key]
    }
  },
  {immediate: true}
)

watch(
  () => props.modelValue,
  (val) => {
    if (!val) {
      for (const key of connection_columns.value) {
        if (key === 'params') {
          form.params = {}
          continue
        }
        if (form[key] !== 'id') {
          form[key] = null
          continue
        }
        form[key] = ''
      }
    }
  }
)
</script>
