import {defineStore} from "pinia";
import {secureFetch} from "@/services/fetch";
import useMessageStore from "@/store/messages";

let notFoundBuffer = new Set<string>()
let notFoundTimer: ReturnType<typeof setTimeout> | null = null

export const useIconStore = defineStore("iconStore", {
  state: () => ({
    icons: [],
    config: [],
    loading: false,
    load_list: [],
    onload: [],
    configLoaded: false,
  }),

  actions: {
    async loadConfig(force = false) {
      this.loading = true;
      if (!force && this.load_list.includes("config")) {
        this.loading = false;
        return;
      }
      this.load_list.push("config");
      if (!this.onload) this.onload = []
      if (this.onload.indexOf("config") !== -1) {
        this.loading = false;
        return
      }
      this.onload.push("config");
      const res = await secureFetch("/api/fonts/config").catch(() => false);
      this.onload = this.onload.filter((item) => item !== "config");
      if (res) {
        this.config = await res.json();
        this.configLoaded = true;
        this._flushNotFound()
      }
      this.loading = false;
    },

    async loadIconsWithMeta(force = false) {
      this.loading = true;
      if (!force && this.load_list.includes("icons")) {
        this.loading = false;
        return;
      }
      this.load_list.push("with-meta");
      if (!this.onload) this.onload = []
      if (this.onload.indexOf("with-meta") !== -1) {
        this.loading = false;
        return
      }
      this.onload.push("with-meta");
      const res = await secureFetch("/api/fonts/icons/with-meta").catch(() => false);
      this.onload = this.onload.filter((item) => item !== "with-meta");
      if (res) {
        this.icons = await res.json();
      }
      this.loading = false;
    },

    async generateFont() {
      const res = await secureFetch("/api/fonts/generate", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
      }).catch(() => false);
      if (res) {
        const messageStore = useMessageStore();
        messageStore.addMessage({
          type: "info",
          text: "Шрифт сгенерирован",
        });
      }
    },

    async updateConfig(newConfig) {
      return await secureFetch("/api/fonts/config", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: newConfig,
      }).catch(() => false);
    },

    async resetConfig() {
      await secureFetch("/api/fonts/reset", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
      }).catch(() => false);
    },

    async deleteIcon(name, folder) {
      return await secureFetch(`/api/fonts/icons/${folder}/${name}`, {
        method: "DELETE",
      });
    },

    async editIcon({filepath, rotate = 0, flip = null}) {
      await secureFetch("/api/fonts/icons/edit", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: {filepath, rotate, flip},
      }).catch(() => false);
    },

    async uploadIcon(file) {
      const res = await secureFetch("/api/fonts/upload", {
        method: "POST",
        body: {},
        files: {file},
      }).catch(() => false);
      return res ? await res.json() : null;
    },

    async renameIcon(old_name, new_name, folder) {
      const res = await secureFetch("/api/fonts/icons/rename", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: {old_name, new_name, folder},
      }).catch(() => false);
      return res ? await res.json() : null;
    },

    async add_to_notfound(name: string) {
      if (!name) return
      notFoundBuffer.add(name)
      if (this.configLoaded) this._flushNotFound()
    },

    reload_style() {
      const id = 'icon-style'
      let el = document.getElementById(id)
      const newHref = `/api/fonts/style.css?t=${Date.now()}`

      if (el) {
        el.href = newHref
      } else {
        el = document.createElement('link')
        el.id = id
        el.rel = 'stylesheet'
        el.href = newHref
        document.head.appendChild(el)
      }
    },

    async _flushNotFound() {
      if (notFoundTimer) clearTimeout(notFoundTimer)
      notFoundTimer = setTimeout(async () => {
        if (!notFoundBuffer.size) return
        const payload = Array.from(notFoundBuffer).filter(icon => {
          const iconConfig = this.config.find(item => item.name === icon)
          return iconConfig && iconConfig.notfound
        })
        notFoundBuffer.clear()
        if (!payload.length) return
        console.log('notFoundBuffer', notFoundBuffer, payload)
        const res = await secureFetch("/api/fonts/icon/notfound", {
          method: "POST",
          body: {'icons': payload},
        })

        if (res) {
          const json = await res.json()
          if (json.status === "ok" && json.updated) {
            await this.loadConfig(true)
            this.reload_style()
          }
        }
      }, 5000)
    }
  },
});
