import { defineStore } from 'pinia'
import { secureFetch } from '@/services/fetch'

export const useErrorStore = defineStore('errorStore', {
  state: () => ({
    groups: [],
    selectedGroup: null,
    selectedLog: null,
    logContent: '',
  }),

  actions: {
    async fetchGroups() {
      const response = await secureFetch('/api/errors')
      const data = await response.json()
      this.groups = data
    },

    selectGroup(group) {
      this.selectedGroup = group
      this.selectedLog = null
      this.logContent = ''
    },

    async selectLog(file) {
      if (!this.selectedGroup) return
      const response = await secureFetch(`/api/errors/${this.selectedGroup.id}/${file}`)
      const data = await response.text() // лог — это plain text
      this.selectedLog = file
      this.logContent = data
    },
  },
})
