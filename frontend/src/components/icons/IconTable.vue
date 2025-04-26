<template>
  <v-card flat>
    <v-row>
      <v-col cols="12" md="3">Всего иконок в базе: {{ icons.length }}</v-col>
      <v-col cols="12" md="3">Всего иконок в конфиге: {{ (config?.icons || []).length }}</v-col>
      <v-col cols="12" md="3">Выбрано иконок: {{ Object.values(localToggles).filter(i => i).length }}</v-col>
      <v-col cols="12" md="3">Отфильтрованно иконок: {{ filteredIcons.length }}</v-col>
    </v-row>
    <v-row class="mb-4" align="center">
      <v-col cols="12" md="3">
        <v-text-field v-model="search" label="Поиск" prepend-icon="mdi-magnify" clearable density="compact"
                      hide-details/>
      </v-col>
      <v-col cols="12" md="3">
        <v-select
          v-model="dir_name"
          :items="dir_list"
          label="Выберите директорию"
          clearable
          density="compact"
          hide-details
        />
      </v-col>
      <v-col cols="12" md="1">
        <v-select
          v-model="perPage"
          :items="[20, 50, 100, 200]"
          label="Иконок на странице"
          density="compact"
          hide-details
        />
      </v-col>
      <v-col cols="12" md="2" class="text-left d-flex">
        <v-btn color="primary" @click="applyConfig">Сохранить изменения</v-btn>
        <v-btn
          color="secondary"
          @click="toggleAllOnPage"
          variant="outlined"
          block
        >
          {{ allSelectedOnPage ? 'Снять выделение' : 'Выделить всё' }}
        </v-btn>
      </v-col>
      <v-col cols="12" md="3" class="text-right">
        <v-btn-toggle v-model="view" mandatory>
          <v-btn value="mini" icon>
            <v-icon>mdi-dots-grid</v-icon>
          </v-btn>
          <v-btn value="grid6" icon>
            <v-icon>mdi-view-grid</v-icon>
          </v-btn>
          <v-btn value="grid12" icon>
            <v-icon>mdi-view-grid-plus</v-icon>
          </v-btn>
          <v-btn value="table" icon>
            <v-icon>mdi-view-list</v-icon>
          </v-btn>
        </v-btn-toggle>
      </v-col>
    </v-row>

    <IconEditor v-model="editDialog" :name="selected?.name" :folder="selected?.folder" @edited="refresh"/>
    <IconRename v-model="renameDialog" :name="selected?.name" :folder="selected?.folder" @renamed="refresh"/>

    <v-data-table
      v-if="view === 'table'"
      :items="paginatedIcons"
      :headers="headers"
      item-value="name"
      density="compact"
      class="elevation-1"
      :items-per-page="perPage"
      hide-default-footer
    >
      <template #item.name="{ item }">
        <div class="d-flex align-center gap-2">
          <m-icon :code="item.name" :folder="item.folder" :type="item.defined ? 'font' : 'svg'" size="42"/>
          <span>{{ item.name }}</span>
        </div>
      </template>
      <template #item.defined="{ item }">
        <v-checkbox
          v-model="localToggles[`${item.folder}/${item.name}`]"
          density="compact"
          hide-details
        />
      </template>
      <template #item.actions="{ item }">
        <v-btn size="small" icon="mdi-pencil" @click="edit(item)"/>
        <v-btn size="small" icon="mdi-rename-box" @click="rename(item)"/>
        <v-btn size="small" icon="mdi-delete" @click="remove(item)"/>
      </template>
    </v-data-table>

    <v-container fluid v-else-if="view === 'mini'">
      <span>
        Для копирования названия иконки зажмите <strong>Ctrl</strong> или <strong>Cmd</strong> и кликните по иконке.<br>
        Также можно выделить иконку двойным кликом.<br>
        Для выделения иконки кликните по ней.<br>
      </span>
      <v-row dense>
        <v-col
          cols="2"
          sm="1"
          v-for="item in paginatedIcons"
          :key="item.name"
        >
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              class="d-flex align-center justify-center card-wrap"
              height="48"
              :color="localToggles[`${item.folder}/${item.name}`] ? 'primary' : undefined"
              @click="handleClick($event,item)"
              @dblclick="copyToClipboard(item)"
            >
              <span class="card-dir">{{ item.folder }}</span>
              <m-icon :code="item.name" :folder="item.folder" :type="item.defined ? 'font' : 'svg'" size="32"/>
              <span class="card-name">{{ item.name }}</span>
            </v-card>
          </v-hover>
        </v-col>
      </v-row>
    </v-container>

    <v-container fluid v-else>
      <v-row>
        <v-col
          v-for="item in paginatedIcons"
          :key="item.name"
          :cols="view === 'grid6' ? 12 : 6"
          :sm="view === 'grid6' ? 6 : 3"
          :md="view === 'grid6' ? 2 : 1"
        >
          <v-card class="pa-3 d-flex flex-column align-center text-center">
            <m-icon :code="item.name" :folder="item.folder"
                    :type="item.defined ? 'font' : 'svg'" :size="view === 'grid6'?36:42"
                    class="mb-2"/>
            <strong class="mb-1 text-truncate">{{ item.name }}</strong>
            <div class="d-flex align-center justify-center">
              <v-checkbox
                v-model="localToggles[`${item.folder}/${item.name}`]"
                hide-details
                density="compact"
                class="me-2"
              />
              <v-btn size="small" icon="mdi-pencil" @click="edit(item)"/>
              <v-btn size="small" icon="mdi-rename-box" @click="rename(item)"/>
              <v-btn size="small" icon="mdi-delete" @click="remove(item)"/>
            </div>
          </v-card>
        </v-col>
      </v-row>
    </v-container>

    <v-pagination
      v-if="totalPages > 1"
      v-model="page"
      :length="totalPages"
      class="mt-4"
      density="comfortable"
    />
  </v-card>
  <v-dialog v-model="deleteDialog" max-width="400">
    <v-card>
      <v-card-title class="text-h6">Удалить иконку</v-card-title>
      <v-card-text>
        Вы уверены, что хотите удалить <strong>{{ selected?.name }}</strong>?
      </v-card-text>
      <v-card-actions>
        <v-spacer/>
        <v-btn text @click="deleteDialog = false">Отмена</v-btn>
        <v-btn color="red" @click="confirmDelete">Удалить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>


<script setup>
import {ref, computed, watch} from 'vue'
import useMessageStore from '@/store/messages'
import IconRename from './IconRename.vue'
import IconEditor from './IconEditor.vue'
import {secureFetch} from "@/services/fetch";
import {useIconStore} from '@/store/iconStore'

const props = defineProps({
  icons: Array,
  config: Object,
})

const emit = defineEmits(['refresh'])

const headers = [
  {title: 'Имя', key: 'name'},
  {title: 'В конфиге', key: 'defined', sortable: false},
  {title: 'Действия', key: 'actions', sortable: false},
]

const view = ref('mini')
const search = ref('')
const page = ref(1)
const perPage = ref(50)
const editDialog = ref(false)
const renameDialog = ref(false)
const selected = ref(null)
const localToggles = ref({})
const dir_name = ref('')

const messageStore = useMessageStore()
const store = useIconStore()

const filteredIcons = computed(() => {
  return props.icons.filter(i => {
    const matchSearch = i.name.toLowerCase().includes(search.value.toLowerCase())
    const fullKey = `${i.folder}/${i.name}`
    const matchDir = !dir_name.value || typeof dir_name.value !== 'string' ||
      dir_name.value === '<в конфиге>' && i.defined ||
      dir_name.value === '<выделены>' && localToggles.value[fullKey] ||
      i.folder === dir_name.value
    return matchSearch && matchDir
  })
})

const totalPages = computed(() => Math.ceil(filteredIcons.value.length / perPage.value))

const dir_list = computed(() => {
  const dirs = new Set()
  dirs.add('<выделены>')
  dirs.add('<в конфиге>')
  props.icons.forEach(icon => {
    const dir = icon.folder
    if (!dir) return
    dirs.add(dir)
  })
  return Array.from(dirs)
})

const paginatedIcons = computed(() => {
  const start = (page.value - 1) * perPage.value
  return filteredIcons.value.slice(start, start + perPage.value)
})

watch(() => props.icons, icons => {
  localToggles.value = {}
  icons.forEach(icon => {
    const key = `${icon.folder}/${icon.name}`
    localToggles.value[key] = icon.defined
  })
}, {immediate: true})

const refresh = () => emit('refresh')

const edit = (item) => {
  selected.value = item
  editDialog.value = true
}

const rename = (item) => {
  selected.value = item
  renameDialog.value = true
}

const toggleInline = (item) => {
  const key = `${item.folder}/${item.name}`
  if (!localToggles.value[key]) {
    // запрещаем выбор одинакового имени из разных папок
    const exists = Object.entries(localToggles.value).some(([k, v]) => {
      return v && k !== key && k.endsWith(`/${item.name}`)
    })
    if (exists) return
  }
  localToggles.value[key] = !localToggles.value[key]
}

const handleClick = (event, item) => {
  if (event.ctrlKey || event.metaKey) {
    copyToClipboard(item)
  } else {
    toggleInline(item)
  }
}

const allSelectedOnPage = computed(() =>
  paginatedIcons.value.every(
    icon => localToggles.value[`${icon.folder}/${icon.name}`]
  )
)

const toggleAllOnPage = () => {
  const value = !allSelectedOnPage.value
  for (const icon of paginatedIcons.value) {
    localToggles.value[`${icon.folder}/${icon.name}`] = value
  }
}

const deleteDialog = ref(false)

const remove = (item) => {
  selected.value = item
  deleteDialog.value = true
}

const confirmDelete = async () => {
  if (await store.deleteIcon(selected.value.name, selected.value.folder)) {
    deleteDialog.value = false
    await refresh()
    messageStore.addMessage({type: 'success', text: `Удалена иконка ${selected.value.name}`})
  }
}

const applyConfig = async () => {
  const newIcons = Object.entries(localToggles.value)
    .filter(([_, value]) => value === true)
    .map(([key]) => {
      const [folder, name] = key.split('/')
      return {folder, name}
    })

  const newConfig = {...props.config, icons: newIcons}
  const result = await secureFetch('/api/fonts/config', {
    method: 'POST',
    body: newConfig
  })
  if (!result.ok) {
    return
  }
  await refresh()
  store.reloadStyleCss()
  messageStore.addMessage({type: 'success', text: 'Изменения сохранены'})
}

const copyToClipboard = (item) => {
  const fullName = `${item.folder}/${item.name}`
  navigator.clipboard.writeText(fullName).then(() => {
    messageStore.addMessage({
      type: 'info',
      text: `Скопировано: ${fullName}`,
    })
  })
}
</script>


<style scoped>
.card-name, .card-dir {
  font-size: 12px;
  font-weight: 500;
  line-height: 1.2;
  background: rgba(0, 0, 0, 0.6);
  position: absolute;
  width: 100%;
  text-align: center;
  opacity: 0;
  transition: opacity 0.3s ease;
  color: white;
  user-select: none;
}

.card-dir {
  top: 0;
}

.card-name {
  bottom: 0;
}

.card-wrap:hover .card-name,
.card-wrap:hover .card-dir {
  opacity: 1;
}
</style>
