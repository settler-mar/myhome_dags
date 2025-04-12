<template>
  <tr class="log_data_line" :class="log.class_list.join(' ')" :line-number="log.lineNumber">
    <td class="log_line">
      {{ log.lineNumber + 1 }}
    </td>
    <td class="log_time">
      {{ log.time }}
    </td>
    <td class="log_su">
      <span v-if="log.su" class="dot" :title="'Источник: socket_utils'"/>
    </td>
    <td class="log_location log_file_name">
      <span v-if="log.file?.name">{{ log.file.name }}</span>
    </td>
    <td class="log_file_line">
      <span v-if="log.file?.line">{{ log.file.line }}</span>
    </td>
    <td class="log_func">
      <span v-if="log.func">{{ log.func }}</span>
    </td>
    <td class="log_json">
      <template v-if="log.type === 'json' && log.data">
        <div class="truncate max-w-[400px] text-xs text-gray-700">
          <button @click="showJson = !showJson" title="Показать полный JSON" class="text-blue-500 ml-2">👁️</button>
          <span
            v-for="(val, key) in previewData"
            :key="key"
            class="mr-2 cursor-pointer"
            @dblclick="emitFilter(key, val)"
          >
            <strong>{{ key }}:</strong>
            <span v-html="formatValue(val)"></span>
          </span>
        </div>
      </template>
      <template v-else-if="log.type === 'text'">
        <div class="truncate max-w-[400px] text-xs text-gray-700">
          <span v-html="log.raw"></span>
        </div>
      </template>
    </td>
  </tr>

  <tr v-if="showJson">
    <td colspan="100%" class="p-2 bg-gray-100 border-t relative">
      <JsonEditorVue v-model="props.log.data" :stringified="false" :readOnly="true"/>
    </td>
  </tr>
</template>

<script setup>
import {ref, computed} from 'vue'
import JsonEditorVue from "json-editor-vue";

const emit = defineEmits(['filter'])
const props = defineProps({
  log: {type: Object, required: true},
  previewKeys: {
    type: Array,
    default: () => ['message', 'level', 'device_id', 'state', 'power', 'voltage', 'temperature']
  }
})

const showJson = ref(false)

const previewData = computed(() => {
  const res = {}
  if (!props.log.data) return res
  for (const key of props.previewKeys) {
    if (key in props.log.data) {
      res[key] = props.log.data[key]
    }
  }
  return res
})

const prettyJson = computed(() => {
  try {
    return JSON.stringify(props.log.data, null, 2)
  } catch {
    return '[Ошибка парсинга JSON]'
  }
})

function emitFilter(key, val) {
  emit('filter', {key, value: val})
}

function formatValue(val) {
  if (val === null || val === undefined) return '<span class="text-gray-400 italic">null</span>'
  if (typeof val === 'object') return '<span class="text-gray-400 italic">[obj]</span>'
  if (typeof val === 'boolean') {
    return `<span class="${val ? 'text-green-600' : 'text-red-600'} font-semibold">${val}</span>`
  }
  if (typeof val === 'number') {
    return `<span class="text-blue-600">${val}</span>`
  }
  const valStr = String(val)
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(valStr)) {
    return `<span class="text-green-600 font-mono">${valStr}</span>` // IP
  }
  if (valStr.length > 50) {
    return `<span class="text-gray-500 italic">${valStr.slice(0, 47)}...</span>`
  }
  return `<span>${valStr}</span>`
}
</script>

<style scoped>
.log_data_line:hover {
  background-color: #a5ffff;
}

.log_line {
  width: 50px;
  text-align: right;
  padding-right: 3px;
  color: #333;
  background-color: #fff8d6;
}

.log_su .dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  background-color: red;
  border-radius: 50%;
  margin: 5px;
}

.log_file_name {
  text-align: right;
  padding-right: 3px;
  padding-left: 5px;
  white-space: nowrap;
  font-size: 0.8em;
}

.log_file_line {
  white-space: nowrap;
  font-size: 0.8em;
  padding-right: 5px;
}

.log_func {
  padding-right: 5px;
  padding-left: 5px;
  white-space: nowrap;
  font-size: 0.8em;
  color: #333;
}

.log_time {
  text-align: right;
  padding: 5px;
  line-height: 1.2em;
  font-size: 0.8em;
}

.log_filtred.log_odd {
  background-color: #95b1ea;
}

.log_filtred.log_even {
  background-color: #d0e1ff;
}


.log_odd {
  background-color: #f3f4f6;
}

.log_even {
  background-color: #ffffff;
}


.log_line {
  width: 50px;
  text-align: right;
  padding-right: 3px;
  color: #333;
  background-color: #fff8d6;
}

.log_data_line:hover {
  background-color: #a5ffff;
}
</style>
