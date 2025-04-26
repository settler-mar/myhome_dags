import {defineStore} from 'pinia';
import {secureFetch} from '@/services/fetch';
import {webSocketService} from '@/services/websocket';
import {reactive, ref} from 'vue';

export const usePortsStore = defineStore('ports', {
  state: () => ({
    ports: reactive({}),   // Реактивные данные портов
    ts_delta: 0,           // Коррекция времени
    now: ref(Date.now() / 1000), // Реактивное текущее время
    timer: null,           // Обновляющийся таймер
    isLoaded: false,       // Уже загружали данные?
    isSubscribed: false,   // Уже подписались на сокет?
  }),

  actions: {
    async loadPorts(force = false) {
      if (this.isLoaded && !force) return;
      this.startTimer()
      this.subscribePorts()
      try {
        const response = await secureFetch('/api/live/ports');
        const data = await response.json();

        if (data['0'] && data['0'].ts) {
          const server_ts = data['0'].ts;
          const local_ts = Date.now() / 1000;
          this.ts_delta = local_ts - server_ts;
        }

        const new_ports = {...data};
        delete new_ports['0'];

        for (const id in new_ports) {
          this.ports[id] = new_ports[id];
        }

        this.isLoaded = true;
      } catch (error) {
        console.warn('Failed to load ports:', error);
      }
    },

    subscribePorts(force = false) {
      if (this.isSubscribed && !force) return;

      webSocketService.onMessage('port', 'in', (data) => {
        if (!data || typeof data !== 'object' || data.pin_id === undefined) {
          return;
        }

        const port_id = data.pin_id;
        const incoming_ts = data.ts || 0;
        const local_ts = Date.now() / 1000;
        const delta = local_ts - incoming_ts;

        if (delta < 0) {
          this.ts_delta += delta;
          console.warn(`Corrected ts_delta by ${delta.toFixed(3)}s`);
        }

        this.ports[port_id] = {
          value: data.value,
          value_raw: data.value_raw,
          ts: incoming_ts,
        };
      });

      this.isSubscribed = true;
    },

    startTimer() {
      if (this.timer) return;
      this.timer = setInterval(() => {
        this.now = Date.now() / 1000;
      }, 1000);
    },

    stopTimer() {
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }
    },

    getTimeDelta(ts) {
      if (!ts) return '';

      const corrected_ts = ts + this.ts_delta;
      let delta = Math.max(0, this.now - corrected_ts);

      const hours = Math.floor(delta / 3600);
      delta %= 3600;
      const minutes = Math.floor(delta / 60);
      const seconds = Math.floor(delta % 60);

      if (hours > 0) {
        return `${hours}h ${minutes}m`;
      } else if (minutes > 0) {
        return `${minutes}m ${seconds}s`;
      } else {
        return `${seconds}s`;
      }
    }
  },

  getters: {
    getPort: (state) => (id) => {
      const port = state.ports[id];
      if (!port) return null;

      const corrected_ts = port.ts ? port.ts + state.ts_delta : null;

      return {
        ...port,
        corrected_ts,
      };
    },
  },
});

export default usePortsStore;
