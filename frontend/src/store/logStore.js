import { defineStore } from 'pinia'
import { secureFetch } from '@/services/fetch'

export const useLogStore = defineStore('logStore', {
  state: () => ({
    tree: {}, // структура: { [year]: { [month]: { [day]: [ {hour, size, lines} ] } } }
    logs: [],
    loading: false,
    error: null,
  }),

  actions: {
    async fetchTree(level = []) {
      this.loading = true
      this.error = null

      const url = '/api/logs/tree' + (level.length ? '/' + level.join('/') : '')

      try {
        const res = await secureFetch(url)
        const data = await res.json()

        if (level.length === 0) {
          for (const year of data) this.tree[year] = {}
        } else if (level.length === 1) {
          const [year] = level
          for (const month of data) this.tree[year][month] = {}
        } else if (level.length === 2) {
          const [year, month] = level
          for (const day of data) this.tree[year][month][day] = []
        } else if (level.length === 3) {
          const [year, month, day] = level
          this.tree[year][month][day] = data
        }
      } catch (err) {
        this.error = 'Ошибка загрузки дерева логов'
        console.error(err)
      } finally {
        this.loading = false
      }
    },

    async fetchLogs(year, month, day, hour) {
      this.loading = true
      this.error = null
      this.logs = []

      let url = '/api/logs/last'
      if (year && month && day && hour) {
        url = `/api/logs/get/${year}/${month}/${day}/${hour}`
      }

      try {
        const res = await secureFetch(url)
        const data = await res.json()
        this.logs = Array.isArray(data) ? data : data.split('\n')
      } catch (err) {
        this.error = 'Ошибка загрузки логов'
        console.error(err)
      } finally {
        this.loading = false
      }
    }
  }
})
