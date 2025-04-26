<template>
  <v-dialog v-model="show" max-width="500">
    <v-card>
      <v-card-title>Редактировать: {{ name }}</v-card-title>
      <v-card-text>
        <v-img :src="iconUrl" max-height="120" class="mb-2"/>
        <v-row>
          <v-col cols="6">
            <v-slider v-model="rotate" label="Поворот" min="-180" max="180" step="5"/>
          </v-col>
          <v-col cols="6">
            <v-select
              v-model="flip"
              :items="['horizontal', 'vertical']"
              label="Отразить"
              clearable
            />
            <v-checkbox v-model="clean" label="Очистить SVG"/>
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-spacer/>
        <v-btn text @click="close">Отмена</v-btn>
        <v-btn color="primary" @click="apply">Применить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import {ref, watch, computed} from 'vue'
import {useIconStore} from '@/store/iconStore'
import useMessageStore from '@/store/messages'

const props = defineProps({
  modelValue: Boolean,
  name: String
})
const emit = defineEmits(['update:modelValue', 'edited'])

const show = ref(false)
const rotate = ref(0)
const flip = ref(null)
const clean = ref(false)

const store = useIconStore()
const messageStore = useMessageStore()

const iconUrl = computed(() => `/api/fonts/icons/${props.name}`)

watch(() => props.modelValue, val => {
  show.value = val
  rotate.value = 0
  flip.value = null
  clean.value = false
})

const apply = async () => {
  await store.editIcon({filepath: props.name, rotate: rotate.value, flip: flip.value, clean: clean.value})
  messageStore.addMessage({type: 'success', text: `Изменения применены к ${props.name}`})
  emit('edited')
  close()
}

const close = () => {
  emit('update:modelValue', false)
}
</script>
