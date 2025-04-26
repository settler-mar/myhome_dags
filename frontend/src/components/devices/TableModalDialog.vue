<template>
  <v-dialog v-model="visible">
    <v-card>
      <v-card-title>
        {{ action?.name }}
        <v-btn @click="loadData" :loading="loading" density="compact" icon="mdi-refresh"/>
      </v-card-title>
      <v-card-text>
        <v-progress-linear
          v-if="loading"
          color="deep-purple-accent-4"
          height="6"
          indeterminate
          rounded
        />
        <div v-if="action?.description" class="mb-2">
          {{ action.description }}
        </div>

        <v-data-table
          :headers="headers"
          :items="rows"
          item-value="id"
          class="elevation-1"
        >
          <template #item.actions="{ item }">
            <ActionHandler
              :actions="action?.actions"
              :params="{
                ...props.params,
                ...item,
              }"/>
          </template>
        </v-data-table>
      </v-card-text>
      <v-card-actions>
        <v-spacer/>
        <v-btn text @click="visible = false">Закрыть</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import {ref, watch} from 'vue'
import {secureFetch} from '@/services/fetch'
import useMessageStore from '@/store/messages'
import {useTableStore} from '@/store/tables'
import ActionHandler from '@/components/devices/ActionHandler.vue'

const props = defineProps({
  action: Object,
  params: Object
})

const emit = defineEmits(['executed', 'close'])
const visible = ref(true)
const loading = ref(false)
const rows = ref([])
const headers = ref([])
const messageStore = useMessageStore()
const tableStore = useTableStore()

watch(visible, (val) => {
  if (!val) emit('close')
})

loadData()

async function loadData() {
  loading.value = true
  try {
    const url = props.action.endpoint.replace(/\{(\w+?)\}/g, (_, k) => props.params[k] ?? '')
    const res = await secureFetch(url)
    rows.value = await res.json()
    headers.value = (props.action.structure || []).map(s => ({title: s.title, key: s.name}))
    if (!headers.value.some(h => h.key === 'actions')) {
      headers.value.push({title: 'Действия', key: 'actions'})
    }
  } catch (e) {
    console.warn('TableModal load error', e)
    messageStore.addMessage({type: 'error', text: 'Не удалось загрузить таблицу'})
    visible.value = false
  } finally {
    loading.value = false
  }
}
</script>
