<template>
  <v-chip
    v-for="action in stateActions"
    :key="action.name"
    class="ml-2"
    :color="action?.color || 'info'"
    size="small"
  >
    <m-icon start small :icon="action.icon"/>
    {{ params[action.key] || '—' }}
  </v-chip>
  <v-spacer/>

  <div class="d-flex align-center">

    <template v-for="(action, index) in inlineActions" :key="index">
      <v-btn
        v-if="['request', 'json_form', 'table_modal'].includes(action.type)"
        :icon="!!action.icon"
        :loading="loadingAction === action.name"
        @click="handleAction(action)"
        class="mr-1"
        :title="action.name"
        :disabled="loadingAction === action.name"
      >
        <m-icon v-if="action.icon" :icon="action.icon"/>
        <span v-else>{{ action.name }}</span>
      </v-btn>
    </template>

    <slot/>

    <v-menu v-if="menuActions.length" location="bottom">
      <template #activator="{ props }">
        <v-btn icon v-bind="props">
          <m-icon icon="mdi-dots-vertical"/>
        </v-btn>
      </template>
      <v-list>
        <v-list-item
          v-for="(action, index) in menuActions"
          :key="index"
          @click="handleAction(action)"
        >
          <m-icon start :icon="action.icon || 'mdi-play-circle'"/>
          {{ action.name }}
        </v-list-item>
      </v-list>
    </v-menu>

    <template v-for="(action, index) in filteredActions" :key="'state-' + index">
      <v-chip
        v-if="action.type === 'state' && showState(action)"
        :color="action?.color || 'info'"
        size="small"
        class="ml-1"
      >
        <m-icon small :icon="action.icon"/>
        {{ liveState[action.key] || '—' }}
      </v-chip>
    </template>

    <JsonFormDialog
      v-if="jsonFormDialog"
      :action="activeAction"
      :params="params"
      @close="jsonFormDialog = false"
      @executed="emit('executed', $event)"
    />

    <TableModalDialog
      v-if="tableModalDialog"
      :action="activeAction"
      :params="params"
      @close="tableModalDialog = false"
      @executed="emit('executed', $event)"
    />

    <!-- Подтверждение и ввод -->
    <v-dialog v-model="inputDialog" max-width="500">
      <v-card>
        <v-card-title>{{ activeAction?.name }}</v-card-title>
        <v-card-text>
          <v-form>
            <v-container>
              <v-row>
                <v-col
                  v-for="(config, key) in activeAction?.input"
                  :key="key"
                  cols="12"
                >
                  <v-select
                    v-if="config.type === 'select'"
                    v-model="inputValues[key]"
                    :label="config.label || key"
                    :items="Object.entries(config.options || {}).map(([value, text]) => ({ title: text, value }))"
                    item-title="title"
                    item-value="value"
                    :required="config.required"
                    :disabled="loadingAction === activeAction?.name"
                  />
                  <v-text-field
                    v-else
                    v-model="inputValues[key]"
                    :label="config.label || key"
                    :type="config.type === 'int' ? 'number' : 'text'"
                    :min="config.min"
                    :max="config.max"
                    :required="config.required"
                    :disabled="loadingAction === activeAction?.name"
                  />
                </v-col>
              </v-row>
            </v-container>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer/>
          <v-btn text @click="inputDialog = false" :disabled="loadingAction === activeAction?.name">Отмена</v-btn>
          <v-btn color="primary" @click="submitAction" :loading="loadingAction === activeAction?.name">Отправить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="confirmDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h6">Подтверждение</v-card-title>
        <v-card-text>Вы уверены, что хотите выполнить действие: <b>{{ activeAction?.name }}</b>?</v-card-text>
        <v-card-actions>
          <v-spacer/>
          <v-btn text @click="confirmDialog = false" :disabled="loadingAction === activeAction?.name">Отмена</v-btn>
          <v-btn color="red darken-1" text @click="confirmAndExecute" :loading="loadingAction === activeAction?.name">
            Подтвердить
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import {ref, computed} from 'vue'
import {secureFetch} from '@/services/fetch'
import useMessageStore from '@/store/messages'
import JsonFormDialog from '@/components/devices/JsonFormDialog.vue'
import TableModalDialog from '@/components/devices/TableModalDialog.vue'
import {useTableStore} from '@/store/tables'
import {objectToFlat} from '@/utils/array'

const props = defineProps({
  actions: Array,
  params: Object
})

const emit = defineEmits(['executed'])
const messageStore = useMessageStore()

const loadingAction = ref(null)
const inputDialog = ref(false)
const confirmDialog = ref(false)
const jsonFormDialog = ref(false)
const tableModalDialog = ref(false)
const activeAction = ref(null)
const inputValues = ref({})
let deferredSubmit = null

const filteredActions = computed(() => props.actions)
const inlineActions = computed(() => props.actions.filter(a => a.type !== 'state' && a.menu !== 1))
const menuActions = computed(() => props.actions.filter(a => a.menu === 1))
const stateActions = computed(() => props.actions.filter(a => a.type === 'state'))

const tableStore = useTableStore()

const liveState = computed(() => objectToFlat(props.params || {}))

function showState(action) {
  const value = liveState?.[action.key]
  return action.show_if_empty || (value !== null && value !== undefined && value !== '')
}

function handleAction(action) {
  activeAction.value = action

  if (action.type === 'json_form') return (jsonFormDialog.value = true)
  if (action.type === 'table_modal') return (tableModalDialog.value = true)

  if (action.input) {
    inputValues.value = Object.fromEntries(Object.entries(action.input).map(([k, v]) => [k, v?.default ?? null]))
    inputDialog.value = true
    return
  }

  if (action.confirm) {
    confirmDialog.value = true
    deferredSubmit = () => executeAction(action)
    return
  }

  executeAction(action)
}

function submitAction() {
  const action = activeAction.value
  // test required
  for (const [key, config] of Object.entries(action.input)) {
    if (config.required && !inputValues.value[key]) {
      messageStore.addMessage({type: 'error', text: `Поле «${config.label || key}» обязательно для заполнения.`})
      return
    }
  }
  if (action.confirm) {
    confirmDialog.value = true
    deferredSubmit = () => executeAction(action, inputValues.value)
    return
  }
  executeAction(action, inputValues.value)
}

function confirmAndExecute() {
  if (deferredSubmit) {
    deferredSubmit()
    deferredSubmit = null
  }
}


async function executeAction(action, body = {}) {
  loadingAction.value = action.name
  let success = false
  try {
    // add parameters to body from props.params[key]
    body = {...body, ...props.params}
    const endpoint = action.endpoint.replace(/\{(\w+?)\}/g, (_, key) => body[key] ?? '')
    const method = (action.method || 'POST').toUpperCase()
    await secureFetch(endpoint, {
      method,
      headers: {'Content-Type': 'application/json'},
      body: ['POST', 'PUT', 'PATCH'].includes(method) ? JSON.stringify(body) : undefined
    })
    inputDialog.value = false
    confirmDialog.value = false
    messageStore.addMessage({type: 'info', text: `Действие «${action.name}» успешно выполнено.`})
    emit('executed', {action})
    if (action?.update_after) {
      for (let do_after of action.update_after.split('|')) {
        if (do_after === 'reload') {
          loadData()
          continue
        }
        if (do_after === 'close') {
          visible.value = false
          continue
        }
        if (do_after.startsWith('table.')) {
          const tableName = do_after.split('.').slice(1).join('.')
          tableStore.reloadTableData(tableName)
        }
      }
    }
    success = true
  } catch (e) {
    console.warn('Action failed', e)
  } finally {
    if (success) confirmDialog.value = false
    loadingAction.value = null
  }
}
</script>
