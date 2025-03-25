<template>
  <div v-if="logs.length">
    <!-- Общие значения -->
    <table v-if="Object.keys(commonFields).length" class="mb-4" style="width: 100%">
      <tr
        v-for="(value, key) in commonFields"
        :key="key"
        class="text-sm text-gray-700 mb-1"
      >
        <td><strong class="text-gray-900">{{ key }}:</strong></td>
        <td class="ml-1 text-gray-800">{{ value }}</td>
      </tr>
    </table>

    <!-- Панель управления -->
    <div class="mb-2 flex flex-wrap gap-4 items-center">
      <div class="flex items-center gap-2">
        <v-select
          v-model="selectedColumns"
          :items="selectableColumnOptions"
          multiple
          chips
          label="Отображаемые поля"
          class="min-w-[200px]"
        />
      </div>

      <button @click="resetSettings" class="text-sm px-2 py-1 bg-red-100 hover:bg-red-200 rounded">
        Сбросить настройки
      </button>
    </div>

    <!-- Таблица -->
    <div class="overflow-auto relative">
      <table class="table-auto w-full border mt-6" style="min-width: 100%">
        <thead>
        <tr>
          <th v-for="col in visibleColumns" :key="col" class="border px-2 py-1 text-left">
            <button
              v-if="col === 'ts'"
              @click="toggleTimeFormat"
              class="text-xl hover:opacity-70"
              title="Переключить формат времени"
            >⏱️
            </button>
            <div v-else-if="filterOptions[col]" class="mt-1">
              <v-select
                v-model="columnFilters[col]"
                :items="filterOptions[col]"
                multiple
                clearable
                :placeholder="col"
                :label="col"
                variant="underlined"
              />
            </div>
            <template v-else>{{ col }}</template>
          </th>
        </tr>
        </thead>
        <tbody>
        <tr v-for="(log, index) in sortedFilteredLogs" :key="index" class="border-t">
          <td v-for="col in visibleColumns" :key="col" class="px-2 py-1">
            <template v-if="col === 'ts'">
              <div>
                <span v-if="logsStore.timeFormat === 'exact'">{{ formatTime(log.ts) }}</span>
                <span v-else>{{ timeAgo(log.ts, ts_now) }}</span>
              </div>
            </template>
            <template v-else-if="col === 'level'">
              <span :title="log.level">{{ levelEmoji(log.level) }}</span>
            </template>
            <template v-else>
              {{ log[col] }}
            </template>
          </td>
        </tr>
        </tbody>
      </table>
    </div>
  </div>
  <div v-else class="text-gray-500">Нет логов для отображения</div>
</template>

<script>
import {mapStores} from 'pinia';
import logsStore from '@/store/logs';

const LOCAL_KEY = 'daglogs.settings';

export default {
  props: {
    logs: {
      type: Array,
      required: true
    },
    ignoreColumns: {
      type: Array,
      default: () => ['level', 'permission', 'device_id', 'dag_id', 'type']
    },
    listCanBeGlobalParams: {
      type: Array,
      default: () => ['class_name', 'message']
    }
  },
  data() {
    return {
      selectedColumns: [],
      levelFilterSelect: '',
      columnFilters: {},
      fixedColumns: ['ts', 'level'],
      ts_now: Date.now() / 1000
    };
  },

  computed: {
    ...mapStores(logsStore),


    allColumns() {
      const keys = new Set();
      this.logs.forEach(log => {
        Object.keys(log).forEach(k => keys.add(k));
      });
      const dynamic = Array.from(keys).filter(k => !this.fixedColumns.includes(k));
      return [...this.fixedColumns, ...dynamic];
    },

    selectableColumnOptions() {
      const commonKeys = Object.keys(this.commonFields);
      return this.allColumns.filter(k =>
        !this.fixedColumns.includes(k) &&
        !this.ignoreColumns.includes(k) &&
        !commonKeys.includes(k)
      );
    },

    visibleColumns() {
      const common = Object.keys(this.commonFields);
      if (this.selectedColumns.length === 0) return [...this.fixedColumns, ...this.selectableColumnOptions.filter(col => !common.includes(col))];
      return [...this.fixedColumns, ...this.selectedColumns.filter(col => !common.includes(col))];
    },

    commonFields() {
      const result = {};
      if (this.logs.length === 0) return result;
      const first = this.logs[0];
      for (const key in first) {
        if (
          this.ignoreColumns.includes(key) ||
          !this.listCanBeGlobalParams.includes(key)
        ) continue;
        if (this.logs.every(log => log[key] === first[key])) {
          result[key] = first[key];
        }
      }
      return result;
    },


    allLevels() {
      return Array.from(new Set(this.logs.map(log => log.level).filter(Boolean)));
    },

    filterOptions() {
      const options = {};
      this.visibleColumns.forEach(col => {
        const values = new Set(this.logs.map(l => l[col]).filter(Boolean));
        if (values.size > 1 && values.size <= 10) {
          options[col] = Array.from(values);
        }
      });
      return options;
    },

    filteredLogs() {
      let result = this.logs;
      if (this.levelFilterSelect) {
        result = result.filter(log => log.level === this.levelFilterSelect);
      }
      Object.entries(this.columnFilters).forEach(([col, values]) => {
        if (Array.isArray(values) && values.length > 0) {
          result = result.filter(log => values.includes(log[col]));
        }
      });
      return result;
    },

    sortedFilteredLogs() {
      return [...this.filteredLogs].sort((a, b) => b.ts - a.ts);
    },

  },

  watch: {
    selectedColumns: {
      deep: true,
      handler() {
        this.saveSettings();
      }
    }
  },

  mounted() {
    this.loadSettings();
    setInterval((el) => {
      el.ts_now = Date.now() / 1000;
    }, 500, this);
  },

  methods: {
    toggleTimeFormat() {
      const newFormat = this.logsStore.timeFormat === 'exact' ? 'ago' : 'exact';
      this.logsStore.timeFormat = newFormat;
      this.saveSettings();
    },

    resetSettings() {
      localStorage.removeItem(LOCAL_KEY);
      this.selectedColumns = this.selectableColumnOptions;
      this.levelFilterSelect = '';
      this.columnFilters = {};
      this.logsStore.timeFormat = 'exact';
    },

    formatTime(ts) {
      const date = new Date(ts * 1000);
      return date.toISOString().substr(11, 12);
    },

    timeAgo(ts) {
      const diff = this.ts_now - ts;
      if (diff < 60) return `${Math.floor(diff)}s`;
      if (diff < 3600) return `${Math.floor(diff / 60)}m${Math.floor(diff % 60)}s`;
      return `${Math.floor(diff / 3600)}h${Math.floor((diff % 3600) / 60)}m`;
    },

    levelEmoji(level) {
      switch (level) {
        case 'info':
          return 'ℹ️';
        case 'warning':
          return '⚠️';
        case 'error':
          return '❌';
        case 'debug':
          return '🐞';
        case 'value':
          return '📈';
        default:
          return '❓';
      }
    },

    saveSettings() {
      const payload = {
        selectedColumns: this.selectedColumns,
        timeFormat: this.logsStore.timeFormat
      };
      localStorage.setItem(LOCAL_KEY, JSON.stringify(payload));
    },

    loadSettings() {
      const raw = localStorage.getItem(LOCAL_KEY);
      const defaults = this.selectableColumnOptions;
      if (!raw) {
        this.selectedColumns = defaults;
        return;
      }
      try {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed.selectedColumns)) {
          this.selectedColumns = parsed.selectedColumns.filter(k => defaults.includes(k));
        } else {
          this.selectedColumns = defaults;
        }
        if (parsed.timeFormat === 'exact' || parsed.timeFormat === 'ago') {
          this.logsStore.timeFormat = parsed.timeFormat;
        }
      } catch (e) {
        console.warn('Не удалось загрузить настройки:', e);
        this.selectedColumns = defaults;
      }
    }
  }
};
</script>

<style scoped>
table {
  border-collapse: collapse;
}

th,
td {
  border: 1px solid #ccc;
}
</style>
