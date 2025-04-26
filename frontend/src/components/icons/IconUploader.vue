<template>
  <v-card class="pa-4 mb-4" flat>
    <v-file-input
      v-model="file"
      accept=".svg,.woff,.woff2"
      label="Загрузить иконку / шрифт (.svg, .woff, .woff2)"
      prepend-icon="mdi-upload"
      @change="upload"
    >
      <template v-slot:append-inner>
        <v-btn
          :disabled="!file"
          class="mt-2"
          color="primary"
          @click="upload"
        >
          Загрузить
        </v-btn>
      </template>
    </v-file-input>

    <v-progress-linear
      v-if="onload"
      :active="true"
      :indeterminate="true"
      color="primary"
      height="4"
    />

    <v-alert
      v-if="result"
      type="info"
      class="mt-3"
    >
      Загружено: {{ result.uploaded }}<br/>
      Папка: {{ result.folder }}<br/>
      <template v-if="result.saved_as">Сохранено как: {{ result.saved_as }}<br/></template>
      Режим: {{ result.mode }}<br/>
      Размер: {{ result.size }}<br/>
      <template v-if="result.count">Число иконок: {{ result.count }}</template>
    </v-alert>
  </v-card>
</template>

<script setup>
import {ref} from 'vue'
import {useIconStore} from '@/store/iconStore'

const emit = defineEmits(['uploaded'])
const store = useIconStore()
const file = ref(null)
const result = ref(null)
const onload = ref(false)

const upload = async () => {
  if (!file.value) return
  onload.value = true
  result.value = await store.uploadIcon(file.value)
  onload.value = false
  if (result.value) {
    emit('uploaded')
  }
  file.value = null
}
</script>
