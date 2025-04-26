<template>
  <v-container fluid>
    <h2 class="text-h5 mb-4">Управление иконками</h2>

    <IconUploader @uploaded="refresh"/>
    <v-divider class="my-4"/>
    <IconTable :icons="store.icons" :config="store.config" @refresh="refresh"/>
  </v-container>
</template>

<script setup>
import {onMounted} from 'vue'
import IconUploader from '@/components/icons/IconUploader.vue'
import IconTable from '@/components/icons/IconTable.vue'
import {useIconStore} from '@/store/iconStore'

const store = useIconStore()
const refresh = async () => {
  await store.loadIconsWithMeta(true)
  await store.loadConfig(true)
}

onMounted(refresh)
</script>

<style scoped>
</style>
