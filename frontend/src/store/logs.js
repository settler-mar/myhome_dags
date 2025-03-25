import {defineStore} from "pinia";
import {ref, computed} from "vue";
import {webSocketService} from "@/services/websocket";

export const useLogsStore = defineStore('logs', {
  state: () => ({
    initialized: false,
    by_dag: ref({}),
    by_dags_ports: ref({}),
    timeFormat: ref('exact')
  }),
  created() {
    console.log('logs store created');
    this.initialize();
  },
  actions: {
    toggleTimeFormat() {
      this.timeFormat.value = this.timeFormat.value === 'exact' ? 'ago' : 'exact';
    },
    setupWebSocket() {
      webSocketService.onMessage("log", '', this._get_log);
    },
    _get_log(payload) {
      if (typeof payload.dag_id !== 'undefined') {
        let dag_id = payload.dag_id;
        // if dag_id is string and is number  convert to int
        if (!isNaN(parseInt(dag_id))) {
          dag_id = parseInt(dag_id);
        }
        if (typeof this.by_dag[dag_id] === 'undefined') {
          this.by_dag[dag_id] = [];
        }
        this.by_dag[dag_id].push(payload);

        if (this.by_dag[dag_id].length > 1000) {
          this.by_dag[dag_id].shift();
        }

        if (typeof payload.dag_port_id !== 'undefined') {
          if (typeof this.by_dags_ports[payload.dag_id] === 'undefined') {
            this.by_dags_ports[payload.dag_id] = {
              'in': {},
              'out': {},
              'params': {},
            };
          }
          let direction = payload.direction
          this.by_dags_ports[payload.dag_id][direction][payload.dag_port_id] = payload;
        }
      }
      console.log("log", payload);
    },
    async initialize() {
      if (!this.initialized) {
        this.setupWebSocket();
        this.initialized = true;
      }
    }
  }
});

export default useLogsStore;
