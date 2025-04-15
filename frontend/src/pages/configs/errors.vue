<template>
  <div class="app-layout">
    <aside>
      <h3>Groups</h3>
      <input v-model="filter" placeholder="Search..." style="width: 100%"/>

      <label>Filter by type:</label>
      <select v-model="selectedType" style="width: 100%; margin-bottom: 10px">
        <option value="">All ({{ typeCounts.total }})</option>
        <option v-for="(count, type) in typeCounts.types" :key="type" :value="type">
          {{ type }} ({{ count }})
        </option>
      </select>

      <label>Sort by:</label>
      <select v-model="sortBy" style="width: 100%; margin-bottom: 10px">
        <option value="latest">Latest</option>
        <option value="count">Count</option>
        <option value="type">Type</option>
      </select>

      <div style="margin-bottom: 10px">
        <button @click="refresh">Refresh</button>
        <label style="font-size: 13px">
          <input type="checkbox" v-model="autoRefresh"/> Auto refresh (5s)
        </label>
      </div>

      <ul>
        <li
          v-for="g in sortedGroups"
          :key="g.id"
          @click="selectGroup(g)"
          :class="{ selected: g.id === store.selectedGroup?.id, new: isNewGroup(g.id) }"
        >
          <div class="preview">
            <span :class="['tag', tagColor(extractType(g.preview))]">
              {{ extractType(g.preview) }}
            </span>
            <span class="text">{{ trimPreview(g.preview) }}</span>
          </div>
          <small>{{ formatDate(g.latest) }} ({{ g.count }})</small>
        </li>
      </ul>
    </aside>

    <section v-if="store.selectedGroup">
      <h3>Logs</h3>
      <ul>
        <li
          v-for="file in store.selectedGroup.files"
          :key="file"
          @click="selectLog(file)"
          :class="{ selected: file === store.selectedLog }"
        >
          {{ file }}
        </li>
      </ul>
    </section>

    <main>
      <h3>Details</h3>

      <div class="block" v-if="parsed && (parsed.locals.length || parsed.request.length)">
        <details open>
          <summary><strong>Locals</strong></summary>
          <table v-if="parsed.locals.length">
            <tr v-for="[k, v] in parsed.locals" :key="k">
              <td><strong>{{ k }}</strong></td>
              <td><code v-html="highlightCode(escapeHtml(v))"></code></td>
              <td>
                <button @click="copy(v)">📋</button>
              </td>
            </tr>
          </table>
        </details>

        <details open>
          <summary><strong>Request Context</strong></summary>
          <table v-if="parsed.request.length">
            <template v-for="[k, v] in parsed.request">
              <tr :key="k" v-if="!['headers','cookies','query_params'].includes(k)">
                <td><strong>{{ k }}</strong></td>
                <td>
                  <code v-html="highlightCode(escapeHtml(v))"/>
                </td>
                <td>
                  <button @click="copy(v)">📋</button>
                </td>
              </tr>
            </template>
            <tr v-if="json_view_data.headers">
              <td>
                <strong>Headers</strong>
              </td>
              <td>
                <JsonEditorVue v-model="json_view_data.headers" :stringified="false" :readOnly="true"/>
              </td>
            </tr>
            <tr v-if="json_view_data.cookies">
              <td>
                <strong>Cookies</strong>
              </td>
              <td>
                <JsonEditorVue v-model="json_view_data.cookies" :stringified="false" :readOnly="true"/>
              </td>
            </tr>
            <tr v-if="json_view_data.query_params">
              <td>
                <strong>Query Params</strong>
              </td>
              <td>
                <JsonEditorVue v-model="json_view_data.query_params" :stringified="false" :readOnly="true"/>
              </td>
              <td>
                <button @click="copy(json_view_data.query_params.toString())">📋</button>
              </td>
            </tr>
          </table>
        </details>
      </div>

      <div v-if="store.selectedLog">
        <button @click="downloadLog">Download</button>
      </div>

      <details>
        <summary><strong>Full Log</strong></summary>
        <pre v-if="store.logContent"><code v-html="highlightCode(escapeHtml(store.logContent))"></code></pre>
      </details>
    </main>
  </div>
</template>

<script setup>
import {ref, computed, onMounted} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {useErrorStore} from '@/store/errorStore'
import JsonEditorVue from "json-editor-vue";

const store = useErrorStore()
const route = useRoute()
const router = useRouter()

const filter = ref('')
const selectedType = ref('')
const sortBy = ref('latest')
const autoRefresh = ref(false)
let lastGroupIds = ref(new Set())
const newGroups = ref(new Set())

onMounted(() => {
  refresh().then(() => {
    const groupId = route.params.groupId
    const logFile = route.params.logFile
    if (groupId) {
      const group = store.groups.find(g => g.id === groupId)
      if (group) {
        store.selectGroup(group)
        if (logFile) store.selectLog(logFile)
      }
    }
  })
  setInterval(() => {
    if (autoRefresh.value) refresh()
  }, 5000)
})

function refresh() {
  return store.fetchGroups().then(() => {
    const currentIds = new Set(store.groups.map(g => g.id))
    newGroups.value = new Set([...currentIds].filter(id => !lastGroupIds.value.has(id)))
    lastGroupIds.value = currentIds
  })
}

function selectGroup(group) {
  store.selectGroup(group)
  router.push(`/configs/errors/${group.id}`)
}

function selectLog(file) {
  const group = store.selectedGroup
  if (!group) return
  store.selectLog(file)
  router.push(`/configs/errors/${group.id}/${file}`)
}

function extractType(preview) {
  const match = preview?.match(/\[Exception\]: (\w+):/)
  return match?.[1] || 'Unknown'
}

function trimPreview(preview) {
  return preview?.replace(/\[Exception\]: \w+: /, '') || ''
}

function formatDate(isoStr) {
  if (!isoStr) return ''
  const date = new Date(isoStr)
  return date.toLocaleString()
}

function isNewGroup(id) {
  return newGroups.value.has(id)
}

const typeCounts = computed(() => {
  const map = {}
  for (const g of store.groups) {
    const type = extractType(g.preview)
    map[type] = (map[type] || 0) + 1
  }
  return {
    total: store.groups.length,
    types: map,
  }
})

const filteredGroups = computed(() => {
  return store.groups.filter(g => {
    const type = extractType(g.preview)
    const matchesText = g.preview?.toLowerCase().includes(filter.value.toLowerCase()) ||
      g.id?.toLowerCase().includes(filter.value.toLowerCase())
    const matchesType = selectedType.value === '' || selectedType.value === type
    return matchesText && matchesType
  })
})

const sortedGroups = computed(() => {
  const sorted = [...filteredGroups.value]
  if (sortBy.value === 'latest') {
    sorted.sort((a, b) => (b.latest || '').localeCompare(a.latest || ''))
  } else if (sortBy.value === 'count') {
    sorted.sort((a, b) => (b.count || 0) - (a.count || 0))
  } else if (sortBy.value === 'type') {
    sorted.sort((a, b) => extractType(a.preview).localeCompare(extractType(b.preview)))
  }
  return sorted
})

const parsed = computed(() => {
  if (!store.logContent) return null
  const lines = store.logContent.split('\n')
  let locals = []
  let request = []
  let block = null
  for (let line of lines) {
    if (line.startsWith('[Locals]')) block = 'locals'
    else if (line.startsWith('[Request Context]')) block = 'request'
    else if (line.startsWith('[')) block = null
    else if (block && line.trim()) {
      if (block === 'request') {
        const delimiter_pos = line.indexOf(':')
        const key = line.slice(0, delimiter_pos).trim()
        let val = line.slice(delimiter_pos + 1).trim()

        if (key === 'headers' || key === 'cookies' || key === 'query_params') {
          // request.push([key, parseKeyValueBlock(val)])
          //request.push([key, val])
          const raw_val = val
          try {
            val = JSON.parse(val.replace("'", '"').replace(/'/g, '"'))
          } catch (e) {
            console.error('Error parsing JSON:', e)
            val = raw_val
          }
        }
        request.push([key, val])

        continue
      }
      const [k, ...v] = line.split('=')
      const key = k?.trim().replace(':', '')
      const val = v.join('=').trim()
      if (block === 'locals') locals.push([key, val])
    }
  }
  return {locals, request}
})

const json_view_data = computed(() => {
  const headers = parsed.value.request.find(r => r[0] === 'headers')
  const cookies = parsed.value.request.find(r => r[0] === 'cookies')
  const query_params = parsed.value.request.find(r => r[0] === 'query_params')
  return {
    headers: headers ? headers[1] : null,
    cookies: cookies ? cookies[1] : null,
    query_params: query_params ? query_params[1] : null
  }

})

function tagColor(type) {
  const colors = {
    ZeroDivisionError: 'red',
    KeyError: 'orange',
    ValueError: 'yellow',
    TypeError: 'blue',
    RuntimeError: 'purple',
    Unknown: 'gray',
  }
  return colors[type] || 'gray'
}

function copy(text) {
  navigator.clipboard.writeText(text)
}

function downloadLog() {
  if (!store.logContent) return
  const blob = new Blob([store.logContent], {type: 'text/plain'})
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = store.selectedLog || 'log.txt'
  a.click()
  URL.revokeObjectURL(url)
}

function escapeHtml(str) {
  return str?.replace(/[&<>"']/g, s => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  }[s])) || ''
}

function highlightCode(text) {
  if (!text) return ''
  return text.replace(/(Traceback|File .*?line \d+|Exception:.*?)\n/g, '<span style="color: #d14">$1</span><br>')
    .replace(/\n/g, '<br>')
    .replace(/ /g, '&nbsp;')
    .replace(/(".*?")/g, '<span style="color: #1a1">$1</span>')
    .replace(/(\bTrue\b|\bFalse\b|\bNone\b)/g, '<span style="color: #00c">$1</span>')
}

function parseKeyValueBlock(text) {
  const result = {}
  const lines = text.split(';')
  for (let line of lines) {
    const [key, ...val] = line.split('=')
    if (key && val.length) result[key.trim()] = val.join('=').trim()
  }
  return result
}
</script>

<style scoped>
.inner-table td.wrap {
  word-break: break-all;
  white-space: pre-wrap;
}

.app-layout {
  display: flex;
  height: 100vh;
  font-family: sans-serif;
}

aside,
section {
  width: 300px;
  padding: 10px;
  overflow-y: auto;
  border-right: 1px solid #ccc;
}

main {
  flex: 1;
  padding: 10px;
  overflow-y: auto;
  background: #fafafa;
}

.selected {
  font-weight: bold;
  background: #e8e8ff;
  cursor: pointer;
}

.new {
  animation: highlight 1s ease-in-out;
  border-left: 4px solid green;
}

@keyframes highlight {
  from {
    background-color: #e0ffe0;
  }
  to {
    background-color: inherit;
  }
}

input, select {
  margin-bottom: 10px;
}

table {
  border-collapse: collapse;
  width: 100%;
}

td {
  border: 1px solid #ccc;
  padding: 4px 6px;
  vertical-align: top;
}

details summary {
  cursor: pointer;
  font-size: 16px;
  margin: 10px 0 5px;
}

button {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
}

.preview {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 4px;
}

.tag {
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: bold;
  color: white;
}

.red {
  background-color: #e74c3c;
}

.orange {
  background-color: #e67e22;
}

.yellow {
  background-color: #f1c40f;
  color: #333;
}

.blue {
  background-color: #3498db;
}

.purple {
  background-color: #9b59b6;
}

.gray {
  background-color: #7f8c8d;
}
</style>
<script setup>
</script>
<script setup>
</script>
