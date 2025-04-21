<template>
  <v-dialog v-model="show" max-width="400">
    <v-card>
      <v-card-title>Переименование</v-card-title>
      <v-card-text>
        {{ folder }}
        <v-text-field
          v-model="newName"
          label="Новое имя"
          :rules="[v => !!v || 'Имя обязательно']"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer/>
        <v-btn text @click="show = false">Отмена</v-btn>
        <v-btn color="primary" @click="confirm">Сохранить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import {ref, watch} from 'vue'
import {useIconStore} from '@/store/iconStore'
import useMessageStore from '@/store/messages'

const props = defineProps({
  modelValue: Boolean,
  name: String,
  folder: String
})
const emit = defineEmits(["update:modelValue", "renamed"])

const show = ref(false)
const newName = ref("")
const store = useIconStore()
const messageStore = useMessageStore()

watch(() => props.modelValue, val => {
  show.value = val
  newName.value = props.name || ""
})

const confirm = async () => {
  if (!newName.value || newName.value === props.name) return
  const result = await store.renameIcon(props.name, newName.value, props.folder)
  if (result) {
    messageStore.addMessage({type: 'success', text: `Переименовано: ${result.from} → ${result.to}`})
    emit("renamed")
  }
  show.value = false
  emit("update:modelValue", false)
}
</script>
