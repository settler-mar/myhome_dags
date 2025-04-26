<template>
  <v-dialog v-model="dialog" max-width="400">
    <template #activator="{ props }">
      <v-btn color="red" icon v-bind="props">
        <v-icon>mdi-delete</v-icon>
      </v-btn>
    </template>

    <v-card>
      <v-card-title class="text-h6">Удалить запись?</v-card-title>
      <v-card-text>
        Вы действительно хотите удалить эту запись из таблицы <strong>{{ table }}</strong>?
      </v-card-text>
      <v-card-actions>
        <v-spacer/>
        <v-btn text @click="dialog = false">Отмена</v-btn>
        <v-btn color="red" @click="confirmDelete">Удалить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import {ref} from 'vue'
import {useTableStore} from '@/store/tables'

const props = defineProps({
  id: {type: [String, Number], required: true},
  table: {type: String, required: true}
})
const emit = defineEmits(['deleted'])
const dialog = ref(false)

const store = useTableStore()

const confirmDelete = async () => {
  await store.deleteItem(props.table, props.id)
  emit('deleted')
  store.reloadTableData(props.table)
  dialog.value = false
}
</script>
