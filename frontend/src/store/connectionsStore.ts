import { defineStore } from 'pinia'
import { secureFetch } from '@/services/fetch'

export const useConnectionsStore = defineStore('connectionsStore', {
  state: () => ({
    available: [],      // данные с /api/connections_list
    live: [],           // данные с /api/live/connections
    loading: false,
    error: null,
  }),

  actions: {
    async fetchAvailable() {
      this.loading = true
      this.error = null
      try {
        const res = await secureFetch('/api/connections_list')
        this.available = await res.json()
      } catch (e) {
        console.warn(e)
        this.error = 'Ошибка при загрузке доступных подключений'
      } finally {
        this.loading = false
      }
    },

    async fetchLive() {
      this.loading = true
      this.error = null
      try {
        const res = await secureFetch('/api/live/connections')
        this.live = await res.json()
      } catch (e) {
        console.warn(e)
        this.error = 'Ошибка при получении состояния подключений'
      } finally {
        this.loading = false
      }
    }
  }
})
