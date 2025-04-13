import {defineStore} from 'pinia'

export const useStatusStore = defineStore('status', {
  state: () => ({
    system: {
      loading: false,
      error: null,
      cpu: {
        per_core_usage_percent: [],
        load_avg_1_5_15: [],
        physical_cores: 0,
        logical_cores: 0,
        frequency_mhz: {}
      },
      memory: {
        total: 0,
        used: 0,
        percent: 0
      },
      disks: {},
      os: {},
      hostname: '',
      platform: '',
      boot_time: '',
      uptime_minutes: 0,
      users: [],
      processes: [],
      sensors: {},
      network: {
        interfaces: [],
        wifi_networks: [],
        connections: []
      },
      gpu: []
    },
    docker: {
      containers: [],
      host: {}
    }
  }),

  actions: {
    async loadStatus() {
      this.system.loading = true
      this.system.error = null
      try {
        const res = await fetch('/api/status/system')
        const data = await res.json()
        this.system = {
          ...this.system,
          ...data,
          loading: false,
          error: null
        }
      } catch (e) {
        this.system.loading = false
        this.system.error = 'Ошибка загрузки данных системы'
      }
    },

    async loadDocker() {
      try {
        const res = await fetch('/api/status/docker')
        const data = await res.json()
        this.docker = data
      } catch (e) {
        console.warn('Ошибка загрузки Docker', e)
      }
    },

    async loadCpuMemory() {
      try {
        const res = await fetch('/api/status/system_status')
        const data = await res.json()
        this.system.cpu.per_core_usage_percent = Array.isArray(data.cpu.usage) ? data.cpu.usage : []
        this.system.memory.percent = data.memory.percent
        this.system.memory.used = data.memory.used
        this.system.memory.total = data.memory.total
      } catch (e) {
        console.warn('Ошибка обновления CPU/Memory', e)
      }
    },

    async loadWifi() {
      try {
        const res = await fetch('/api/status/wifi')
        const data = await res.json()
        this.system.network.wifi_networks = data
      } catch (e) {
        console.warn('Ошибка загрузки WiFi сетей', e)
      }
    }
  }
})
