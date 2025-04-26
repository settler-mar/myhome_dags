<template>
  <v-dialog v-model="visible" max-width="600">
    <v-card>
      <v-card-title>
        {{ action?.name }}
      </v-card-title>
      <v-card-text>
        <v-form>
          <v-container>
            <v-row>
              <v-col
                v-for="(value, key) in jsonForm"
                :key="key"
                cols="12"
              >
                <v-text-field
                  v-model="jsonForm[key]"
                  :label="key"
                  :disabled="loading"
                />
              </v-col>
            </v-row>
          </v-container>
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer/>
        <v-btn text @click="close" :disabled="loading">Отмена</v-btn>
        <v-btn color="primary" @click="submit" :loading="loading">Сохранить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import {ref, watch} from 'vue'
import {secureFetch} from '@/services/fetch'
import useMessageStore from '@/store/messages'

const props = defineProps({
  action: Object,
  params: Object
})

const emit = defineEmits(['executed', 'close'])

const visible = ref(true)
const loading = ref(false)
const jsonForm = ref({})
const messageStore = useMessageStore()

watch(visible, (val) => {
  if (!val) emit('close')
})

loadJson()

async function loadJson() {
  loading.value = true
  try {
    const url = props.action.endpoint.replace(/\{(\w+?)\}/g, (_, k) => props.params[k] ?? '')
    const res = await secureFetch(url)
    jsonForm.value = await res.json()
  } catch (e) {
    console.warn('Failed to load JSON', e)
    messageStore.addMessage({type: 'error', text: 'Не удалось загрузить параметры'})
    visible.value = false
  } finally {
    loading.value = false
  }
}

async function submit() {
  loading.value = true
  try {
    const url = props.action.submit_endpoint.replace(/\{(\w+?)\}/g, (_, k) => props.params[k] ?? '')
    await secureFetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(jsonForm.value)
    })
    messageStore.addMessage({type: 'info', text: `Действие «${props.action.name}» успешно выполнено.`})
    emit('executed', {action: props.action})
    visible.value = false
  } catch (e) {
    console.warn('Submit failed', e)
  } finally {
    loading.value = false
  }
}

function close() {
  visible.value = false
}
</script>
