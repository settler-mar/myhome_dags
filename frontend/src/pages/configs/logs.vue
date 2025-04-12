<template>
  <div class="log-viewer">
    <!-- Слева — дерево -->
    <div class="log-tree">
      <h2 class="text-lg font-semibold mb-2">
        📁 Лог-файлы
        <v-btn icon @click="refreshTree" class="ml-2" density="compact" title="Обновить дерево">
          <v-icon>mdi-refresh</v-icon>
        </v-btn>
        <v-btn icon @click="store.loadFullTree()" title="Загрузить всё дерево" density="compact">
          <v-icon>mdi-folder-multiple</v-icon>
        </v-btn>
      </h2>
      <ul class="space-y-1 text-sm">
        <li v-for="year in Object.keys(store.tree).sort()" :key="year">
          <details :open="expanded[year]" @toggle="toggleExpand([year])">
            <summary class="cursor-pointer font-semibold" :class="{ 'active-tree': isActiveLevel([year]) }">
              📁 {{ year }}
            </summary>
            <ul class="ml-4 space-y-1">
              <li v-for="month in Object.keys(store.tree[year]).sort(numericSort)" :key="month">
                <details :open="expanded[`${year}-${month}`]" @toggle="toggleExpand([year, month])">
                  <summary class="cursor-pointer" :class="{ 'active-tree': isActiveLevel([year, month]) }">
                    📁 {{ month }}
                  </summary>
                  <ul class="ml-4 space-y-1">
                    <li v-for="day in Object.keys(store.tree[year][month]).sort(numericSort)" :key="day">
                      <details :open="expanded[`${year}-${month}-${day}`]" @toggle="toggleExpand([year, month, day])">
                        <summary class="cursor-pointer" :class="{ 'active-tree': isActiveLevel([year, month, day]) }">
                          📁 {{ day }}
                        </summary>
                        <ul class="ml-4 space-y-1">
                          <li v-for="log in store.tree[year][month][day].sort((a, b) => a.hour - b.hour)"
                              :key="log.hour">
                            <button
                              @click="selectLog(year, month, day, log.hour)"
                              class="text-sm tree-log-button"
                              :class="{ 'active-log-button': isActiveLevel([year, month, day, log.hour]) }"
                            >
                              🕒 {{ log.hour }}:00 ({{ log.lines }} строк)
                            </button>
                          </li>
                        </ul>
                      </details>
                    </li>
                  </ul>
                </details>
              </li>
            </ul>
          </details>
        </li>
      </ul>
    </div>

    <!-- Справа — логи -->
    <div class="log-content">
      <div class="flex flex-wrap items-center justify-between mb-2 gap-2">
        <h2 class="text-lg font-semibold">
          📄 Логи
        </h2>
        <div class="text-sm text-gray-500" v-if="lastSelection">
          <span>Логи за {{ selectedLogTime }}</span>
        </div>
        <v-row class="flex items-center gap-2" style="align-items: center;">
          <v-switch
            v-model="autoRefresh"
            @change="onToggleAuto"
            color="primary"
            label="автообновление"
            class="auto_update_switch"
          />

          <v-btn @click="refresh" variant="text"
                 v-if="lastSelection">
            🔁 Обновить
          </v-btn>
          <v-btn @click="clearFilters" variant="text"
                 v-if="hasFilters">
            ♻️ Сбросить
          </v-btn>
          <v-menu v-if="availableJsonKeys.length" :close-on-content-click="false">
            <template v-slot:activator="{ props }">
              <v-btn variant="text" v-bind="props">🛠️ Поля JSON</v-btn>
            </template>
            <v-list>
              <v-list-item
                v-for="(key, i) in availableJsonKeys"
                :key="i"
                :value="i"
              >
                <v-switch
                  color="primary"
                  v-model="previewKeys"
                  :value="key"
                  :label="key"
                  hide-details
                />
              </v-list-item>
            </v-list>
          </v-menu>
        </v-row>
      </div>


      <div v-if="lastSelection" class="flex flex-wrap gap-4 items-start mb-3 text-sm">
        <v-row>
          <v-select
            :disabled="activeJsonFilters.length!==0"
            :items="['all', 'json', 'text']"
            label="Типы"
            v-model="filters.type"
            max-width="150"
          ></v-select>
          <v-select
            v-model="filters.filename"
            :items="parsedLogs.map(log => log.file.name).filter((v, i, a) => a.indexOf(v) === i)"
            label="Файл"
            max-width="500"
            clearable
            multiple
            chips
            :placeholder="'Файл (py)'"
          />
          <v-text-field
            v-model="filters.text"
            :counter="100"
            label="Поиск текста"
          ></v-text-field>
          <v-select
            v-model="loadStep"
            :items="[5, 10, 20, 50]"
            label="Догружать строк"
            style="max-width: 150px;"
          />
        </v-row>

        <div v-if="filters.type!=='text'">
          <JsonFilters
            :available-keys="availableJsonKeys"
            :filters="jsonFilters"
            :types="jsonFieldTypes"
            :values="jsonFieldValues"
            @update="applyJsonFilter"
          />
        </div>
      </div>

      <!-- Пагинация (сверху) -->
      <v-row class="flex items-center justify-between mb-2 gap-4" v-if="totalLogs>MIN_TO_PAGINATE">
        <v-col class="flex items-center gap-4">
          <v-select
            v-model="perPage"
            :items="perPageOptions"
            label="Строк на страницу"
            style="max-width: 180px;"
          />
        </v-col>
        <v-col class="flex items-center gap-1">
          {{ (page - 1) * perPage + 1 }} - {{ Math.min(page * perPage, totalLogs) }} / {{ totalLogs }}
        </v-col>
        <v-col>
          <v-pagination
            v-if="totalPages > 1"
            v-model="page"
            :length="totalPages"
            :total-visible="7"
            next-icon="mdi-menu-right"
            prev-icon="mdi-menu-left"
            class="pagination-top"
          />
        </v-col>
      </v-row>


      <!-- Таблица логов -->
      <table v-if="filteredLogs.length"
             class="bg-white border rounded font-mono text-sm overflow-auto h-full w-full log_table"
             cellpadding="0" cellspacing="0"
      >
        <template v-for="(log, index) in filteredLogs" :key="log.lineNumber">
          <tr v-if="getContol(index, -1)" class="log_load_more">
            <td colspan="10" class="text-center">
              <button
                @click="loadMore(-1, log.lineNumber)"
                class="text-blue-600 hover:underline text-sm"
                title="Загрузить выше"
              >
                🔼 Загрузить выше
              </button>
            </td>
          </tr>

          <LogLine :log="log" :previewKeys="previewKeys" @filter="onJsonValueClick"/>

          <tr v-if="getContol(index, 1)" class="log_load_more">
            <td colspan="10" class="text-center">
              <button
                @click="loadMore(1, log.lineNumber)"
                class="text-blue-600 hover:underline text-sm"
                title="Загрузить ниже"
              >
                🔽 Загрузить ниже
              </button>
            </td>
          </tr>
        </template>
      </table>

      <!-- Пагинация (снизу) -->
      <v-pagination
        v-if="totalPages > 1"
        v-model="page"
        :length="totalPages"
        :total-visible="7"
        next-icon="mdi-menu-right"
        prev-icon="mdi-menu-left"
        class="mt-4"
      />

      <div v-if="store.loading" class="text-sm text-gray-500 mt-2">Загрузка...</div>
      <div v-if="store.error" class="text-red-600 mt-2">{{ store.error }}</div>
    </div>
  </div>
</template>


<script setup>
import {reactive, ref, computed, watch, onMounted, onUnmounted} from 'vue'
import {useLogStore} from '@/store/logStore'
import LogLine from '@/components/LogLine.vue'
import JsonFilters from '@/components/JsonFilters.vue'

const MIN_TO_PAGINATE = 1000
/* ——— store / данные ——— */
const store = useLogStore()

/* ——— реактивные переменные ——— */
const expanded = reactive({})
const autoRefresh = ref(false)
const lastSelection = ref(null)
const filters = reactive({filename: [], text: '', type: 'all'})
const visibleIndexes = ref([])
const jsonFilters = ref([])
const previewKeys = ref(['message', 'level', 'device_id', 'power', 'state', 'voltage', 'temperature'])

/* ——— JSON поля ——— */
const availableJsonKeys = ref([])
const jsonFieldTypes = reactive({})
const jsonFieldValues = reactive({})

/* ——— пагинация ——— */
const perPageOptions = [200, 500, 1000, 2000]
const perPage = ref(1000)
const page = ref(1)
const loadStep = ref(10)

let interval = null

const selectedLogTime = computed(() => {
  if (!lastSelection.value) return ''
  const {year, month, day, hour} = lastSelection.value
  const pad = (n) => String(n).padStart(2, '0')
  return `${year}-${pad(month)}-${pad(day)} ${pad(hour)}:00`
})

/* ——— Этап 1: парсинг логов ——— */
const parsedLogs = computed(() => {
  return store.logs.map((str, idx) => {
    const data = {lineNumber: idx}
    let log_parts = str.trim().split(' - ')

    if (log_parts[0].match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})/)) {
      data.time = log_parts.shift()
    }
    if (log_parts[0].includes('(SU)')) {
      data.su = true
      log_parts.shift()
    }
    if (log_parts[1].includes('.py:')) {
      data.func = log_parts.shift()
      const location = (log_parts.shift() || '').split(':')
      data.file = {name: location[0], line: location[1] || ''}
      data.location = `${location[0]}:${location[1] || ''}`
    }

    const raw = log_parts.join(' - ')
    data.raw = raw
    data.type = 'text'

    if ((raw.startsWith('{') && raw.endsWith('}')) || (raw.startsWith('[') && raw.endsWith(']'))) {
      try {
        const parsed = JSON.parse(raw.replace(/'/g, '"'))
        data.data = parsed
        data.type = 'json'

        for (const key in parsed) {
          if (!availableJsonKeys.value.includes(key)) availableJsonKeys.value.push(key)
          if (!(key in jsonFieldTypes)) jsonFieldTypes[key] = typeof parsed[key]
          const valList = jsonFieldValues[key] = jsonFieldValues[key] || new Set()
          if (typeof parsed[key] !== 'object') valList.add(parsed[key])
        }
      } catch {
      }
    }
    return data
  })
})

/* ——— Этап 2: пагинация ——— */
const totalLogs = computed(() => parsedLogs.value.length)
const totalPages = computed(() => totalLogs.value > MIN_TO_PAGINATE ? Math.ceil(totalLogs.value / perPage.value) : 1)

const paginatedLogs = computed(() => {
  if (totalLogs.value <= MIN_TO_PAGINATE) return parsedLogs.value
  const all = parsedLogs.value
  const start = (page.value - 1) * perPage.value
  return all.slice(start, start + perPage.value)
})


/* ——— фильтрация по типу ——— */
function filterLogsType(log) {
  return log.type === filters.type || filters.type === 'all'
}

/* ——— фильтрация по имени файла и тексту ——— */
function filterByFilename(log) {
  return (!filters.filename.length || filters.filename.includes(log.file.name)) &&
    (!filters.text || log.raw.includes(filters.text))
}

/* ——— Этап 4: проставляем флаг фильтрации по тексту и filename ——— */
const withFiltering = computed(() => {
  return paginatedLogs.value.map(log => {
    log.is_filtred = filterByFilename(log) && matchJsonFilters(log) && filterLogsType(log)

    // добавляем class_list
    log.class_list = [
      log.is_filtred && hasFilters.value
        ? 'log_filtred'
        : '',
      log.lineNumber % 2 === 0 ? 'log_even' : 'log_odd'
    ]
    return log
  })
})

/* ——— Этап 5: итоговый результат ——— */
const filteredLogs = computed(() => {
  if (!hasFilters.value) return [...withFiltering.value]

  return withFiltering.value.filter(log =>
    log.is_filtred || visibleIndexes.value.includes(log.lineNumber)
  )
})

/* ——— выбор активных JSON фильтров ——— */
const activeJsonFilters = computed(() => {
  // Фильтр должен быть активным и не пустым
  return jsonFilters.value.filter(filter => filter.active && filter.value && filter.value.length > 0)
})

/* ———  JSON фильтры ——— */
function matchJsonFilters(log) {
  if (!log.data || !Array.isArray(activeJsonFilters.value) || activeJsonFilters.value.length === 0) return true

  if (log.type !== 'json') return false

  for (const filter of activeJsonFilters.value) {
    const value = log.data[filter.key]
    if (value === undefined) return false

    const type = jsonFieldTypes[filter.key]
    const userVal = filter.value

    try {
      if (type === 'number') {
        const actual = parseFloat(value)
        const expected = parseFloat(userVal)
        if (isNaN(actual) || isNaN(expected)) return false
        switch (filter.mode) {
          case '=':
            if (actual !== expected) return false;
            break
          case '!=':
            if (actual === expected) return false;
            break
          case '>':
            if (actual <= expected) return false;
            break
          case '>=':
            if (actual < expected) return false;
            break
          case '<':
            if (actual >= expected) return false;
            break
          case '<=':
            if (actual > expected) return false;
            break
        }
      } else if (type === 'string') {
        const valStr = String(value).toLowerCase()
        const input = String(userVal).toLowerCase()
        switch (filter.mode) {
          case 'contains':
            if (!valStr.includes(input)) return false;
            break
          case 'startsWith':
            if (!valStr.startsWith(input)) return false;
            break
          case 'endsWith':
            if (!valStr.endsWith(input)) return false;
            break
          case '=':
            if (valStr !== input) return false;
            break
          case '!=':
            if (valStr === input) return false;
            break
        }
      } else if (type === 'boolean') {
        if (value !== userVal) return false
      }
    } catch {
      return false
    }
  }

  return true
}


/* ——— Статусы ——— */
const hasFilters = computed(() => {
  return filters.filename.length > 0 || filters.text.length > 0 || activeJsonFilters.value.length > 0 || filters.type !== 'all'
})


/* ——— Методы ——— */
function refreshTree() {
  store.reloadTree()
}

/* ——— Утилиты ——— */
function getContol(index, dir) {
  if (index === 0 && dir < 0) return filteredLogs.value[index].lineNumber !== 0
  if (index === filteredLogs.value.length - 1 && dir > 0)
    return filteredLogs.value[index].lineNumber !== parsedLogs.value.length - 1
  const curr = filteredLogs.value[index].lineNumber
  const next = filteredLogs.value[index + dir].lineNumber
  return next - curr !== dir
}

function loadMore(dir, line_index) {
  console.log('loadMore', dir, line_index)
  for (let i = 0; i < loadStep.value; i++) {
    line_index += dir
    if (line_index < 0 || line_index >= parsedLogs.value.length) break
    if (visibleIndexes.value.includes(line_index)) break
    if (withFiltering.value.find(log => log.lineNumber === line_index).is_filtred) break
    visibleIndexes.value.push(line_index)
  }
}

function isActiveLevel(level) {
  if (!lastSelection.value) return false
  const parts = [lastSelection.value.year, lastSelection.value.month, lastSelection.value.day, lastSelection.value.hour]
  return level.every((val, idx) => String(val) === String(parts[idx]))
}

/* ——— Управление ——— */
function toggleExpand(level) {
  const key = level.join('-')
  if (!expanded[key]) store.fetchTree(level)
  expanded[key] = !expanded[key]
}

function selectLog(year, month, day, hour) {
  lastSelection.value = {year, month, day, hour}
  store.fetchLogs(year, month, day, hour)
  resetVisibleIndexes()
  page.value = 1
}

function refresh() {
  if (lastSelection.value) {
    const {year, month, day, hour} = lastSelection.value
    store.fetchLogs(year, month, day, hour)
  }
}

function onToggleAuto() {
  clearInterval(interval)
  if (autoRefresh.value) interval = setInterval(refresh, 10000)
}

function clearFilters() {
  filters.filename = []
  filters.text = ''
  filters.type = 'all'
  jsonFilters.value = []
  resetVisibleIndexes()
  page.value = 1
}

function resetVisibleIndexes() {
  visibleIndexes.value = []
}

function applyJsonFilter(updatedFilters) {
  jsonFilters.value = updatedFilters
}

function onJsonValueClick({key, value}) {
  jsonFilters.value.push({
    mode: typeof value === 'number' ? '=' : 'contains',
    value,
    key,
    active: true
  })
}

function numericSort(a, b) {
  return parseInt(a) - parseInt(b)
}

/* ——— Watchers ——— */
watch(() => filters.filename, resetVisibleIndexes, {deep: true})
watch(() => filters, resetVisibleIndexes, {deep: true})
watch(() => jsonFilters.value, resetVisibleIndexes, {deep: true})

/* ——— Lifecycle ——— */
onMounted(() => store.fetchTree([]))
onUnmounted(() => clearInterval(interval))
</script>


<style scoped>
.log-viewer {
  display: flex;
  flex-direction: row;
  height: 90vh;
  border: 1px solid #ccc;
  border-radius: 6px;
  overflow: hidden;
  background-color: #f9f9f9;
}

.log-tree {
  width: 320px;
  min-width: 250px;
  max-width: 400px;
  padding: 1rem;
  overflow-y: auto;
  border-right: 1px solid #ddd;
  background-color: white;
}

.log-content {
  flex: 1;
  padding: 1rem;
  overflow: auto;
  background-color: #f3f4f6;
  display: flex;
  flex-direction: column;
}

.log_load_more {
  background-color: #f3f4f6;
  text-align: center;
}

.auto_update_switch {
  margin-bottom: -20px;
}

.log_table {
  text-align: left;
}

.active-tree {
  font-weight: bold;
  color: #2c7be5;
}

.tree-log-button {
  transition: color 0.2s ease;
  background: transparent;
}

.tree-log-button:hover {
  text-decoration: underline;
  background-color: #e5f0ff;
}

.active-log-button {
  color: #1d4ed8; /* blue-700 */
  font-weight: 600;
  background-color: #dbeafe; /* light-blue bg */
}

.log-tree ul {
  list-style: none;
  margin: 0;
  padding-left: 1rem;
  //border-left: 1px solid #ddd;
  position: relative;
}

.log-tree li {
  position: relative;
  margin: 0;
  padding: 0.2rem 0 0.2rem 0;
  margin-left: -0.8rem;
}

.log-tree li::before {
  content: '';
  position: absolute;
  left: -0.2rem;
  top: .8rem;
  width: 0.2rem;
  height: 1px;
  background-color: #ccc;
}

/* Вертикальная линия от родителя к последнему потомку */
.log-tree ul li::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -0.2rem;
  width: 1px;
  background-color: #ddd;
  z-index: 0;
}

/* Обрезаем вертикальную линию у последнего элемента */
.log-tree ul li:last-child::after {
  height: .9rem;
}

</style>
