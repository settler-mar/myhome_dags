import {defineStore} from "pinia";
import {ref, computed} from "vue";
import {webSocketService} from "@/services/websocket";
import useMessageStore from "@/store/messages";
import {secureFetch} from "@/services/fetch";
import {version} from "vue-demi";

const defaultParams = {
  'input': {
    'group': 'input',
    'name': 'default',
    'description': 'Input data',
  },
  'output': {
    'group': 'output',
    'name': 'default',
    'description': 'Output data',
  },
  'param': {
    'group': 'param',
    'name': 'params',
    'description': 'Parameter description',
    'public': true,
  }
}
export const useDagsStore = defineStore("dags", {
  state: () => {
    const dags = ref([]); // Список дагов
    const dags_db = ref([]); // Список блоков дагов
    const templates = ref([]); // Список шаблонов дагов
    const initialized = ref(false); // Флаг инициализации
    const pins_db = ref([]); // список возможных пинов
    return {
      dags,
      dags_db,
      pins_db,
      initialized,
      templates,
      templates_edit: ref({}),
      page: 'main',
      page_collect: ref(['main']),
      select_node: ref(null),
    };
  },
  actions: {
    setPage(page) {
      this.page = page
    },
    // Получение данных при запуске
    async fetchInitialData() {
      const messageStore = useMessageStore();
      try {
        const endpoints = {
          dags: "/api/dags",
          templates: "/api/templates",
          dags_db: "/api/list/dags",
          pins_db: "/api/list/pins",
        };

        const fetchPromises = Object.entries(endpoints).map(async ([key, url]) => {
          const response = await secureFetch(url);
          this[key] = await response.json();
        });

        await Promise.all(fetchPromises);
        this.dags = this.dags.map((dag) => {
          dag.id = dag.id.toString();
          return dag;
        })
      } catch (error) {
        console.error("Ошибка при загрузке данных:", error);
        messageStore.addMessage({type: "error", text: "Ошибка при загрузке данных."});
      }
    },
    _dagUpdate(newDag) {
      newDag.id = newDag.id.toString();
      let id = newDag.id;
      for (let i = 0; i < this.dags.length; i++) {
        if (this.dags[i].id === id) {
          this.dags[i] = newDag;
          console.log("Dag updated", id);
          return;
        }
      }
      this.dags.push(newDag)
      // this.dags = JSON.parse(JSON.stringify(this.dags));
    },
    _dagUpdateParams(data) {
      let id = data.id.toString();
      for (let i = 0; i < this.dags.length; i++) {
        if (this.dags[i].id === id) {
          this.dags[i].params = data.params;
          return;
        }
      }
    },
    _dagDelete(data) {
      if (typeof data !== 'string') data = data.id.toString();
      this.dags = this.dags.filter((dag) => dag.id !== data)
    },
    _templateAdd(newTemplate) {
      this.templates.push(newTemplate);
    },
    // Обновление данных через WebSocket
    setupWebSocket() {
      webSocketService.onMessage("dag", "add", this._dagUpdate);
      webSocketService.onMessage("dag", "update", this._dagUpdate);
      webSocketService.onMessage("dag", "update_params", this._dagUpdateParams);
      webSocketService.onMessage("dag", "remove", this._dagDelete);
      webSocketService.onMessage("template", "add", this._templateAdd);
    },
    get_dag(dag_id) {
      for (let i = 0; i < this.dags.length; i++) {
        if (this.dags[i].id === dag_id) {
          return this.dags[i];
        }
      }
    },
    // Запросы на сервер для работы с дагами
    async addDag(dagName, position) {
      const messageStore = useMessageStore();
      if (this.page.substr(0, 4) === 'tpl:') {
        const page = this.page.substr(4)
        if (dagName.substr(0, 4) === 'tpl.') {
          const template = dagName.substr(4)
          this.templates_edit[page]['template'][template] = this.templates_edit[page]['template'][template] || []
          console.log('addDag', template, defaultParams[template])
          this.templates_edit[page]['template'][template].push({
            id: template + '_' + Math.random().toString(36).substr(2, 9),
            position: [Math.floor(position.x), Math.floor(position.y)],
            ...defaultParams[template]
          })
          return
        }
        this.templates_edit[page]['template']['dags'] = this.templates_edit[page]['template']['dags'] || []
        let params = {}
        for (let param of this.getDagByName(dagName)['params'] || []) {
          params[param['name']] = param['default']
        }
        this.templates_edit[page]['template']['dags'].push({
          id: Math.random().toString(36).substr(2, 9),
          position: [Math.floor(position.x), Math.floor(position.y)],
          name: dagName,
          params,
        })
        return
      }
      try {
        const params = {
          dag_name: dagName,
          position_x: Math.floor(position.x),
          position_y: Math.floor(position.y),
          page: this.page
        };
        const response = await secureFetch(`/api/dags/add`, {
          method: 'post',
          data: params
        });
        const newDag = await response.json();
        this._dagUpdate(newDag);
      } catch (error) {
        console.error("Ошибка при добавлении дага:", error);
        messageStore.addMessage({type: "error", text: "Ошибка при добавлении дага."});
      }
    },
    async removeDag(dagId) {
      if (this.page.substr(0, 4) === 'tpl:') {
        const tpl_name = this.page.substr(4)
        let tpl_group = dagId.split('_')[0]
        if (!['input', 'output', 'param'].includes(tpl_group)) {
          tpl_group = 'dags'
        }
        this.templates_edit[tpl_name]['template'][tpl_group] = this.templates_edit[tpl_name]['template'][tpl_group].filter((dag) => dag.id !== dagId)
        // clear connections
        for (let group_name of ['input', 'param', 'dags']) {
          if (!this.templates_edit[tpl_name]['template'][group_name]) continue
          for (let i = 0; i < this.templates_edit[tpl_name][group_name].length; i++) {
            if (!this.templates_edit[tpl_name]['template'][group_name][i].outputs) continue
            let outputs = {}
            for (let port in this.templates_edit[tpl_name]['template'][group_name][i].outputs) {
              outputs[port] = this.templates_edit[tpl_name]['template'][group_name][i].outputs[port].filter((conn) => conn[1] !== dagId)
            }
            this.templates_edit[tpl_name]['template'][group_name][i].outputs = outputs
          }
        }
        return
      }
      const messageStore = useMessageStore();
      try {
        await secureFetch(`/api/dags/${dagId}`, {method: "DELETE"});
        this._dagDelete(dagId);
      } catch (error) {
        console.error("Ошибка при удалении дага:", error);
        messageStore.addMessage({type: "error", text: "Ошибка при удалении дага."});
      }
    },
    async updateDag(dagId, params) {
      if (typeof dagId !== "string") {
        dagId = dagId.toString();
      }
      if (this.page.substr(0, 4) === 'tpl:') {
        const tpl_name = this.page.substr(4)
        let tpl_group = dagId.split('_')[0]
        if (!['input', 'output', 'param'].includes(tpl_group)) {
          tpl_group = 'dags'
        }
        // console.log('updateDag', dagId, tpl_name, tpl_group, params)
        for (let i = 0; i < this.templates_edit[tpl_name]['template'][tpl_group].length; i++) {
          if (this.templates_edit[tpl_name]['template'][tpl_group][i].id === dagId) {
            for (let key in params) {
              if (key === 'position') {
                this.templates_edit[tpl_name]['template'][tpl_group][i].position = params[key]
              }
              // this.templates_edit[tpl_name]['template'][tpl_group][i][key] = params[key]
            }
          }
        }
        return
      }

      for (let i = 0; i < this.dags.length; i++) {
        if (this.dags[i].id === dagId) {
          this.dags[i] = {...this.dags[i], ...params};
          await secureFetch(`/api/dags/${dagId}`,
            {
              method: "PUT",
              data: {params},
            });
          break;
        }
      }
    },
    async addConnection(from_id, from_type, from_port, to_id, to_type, to_port) {
      console.log('addConnection', from_id, from_type, from_port, to_id, to_type, to_port)
      const messageStore = useMessageStore();
      if (this.page.substr(0, 4) === 'tpl:') {
        const tpl_name = this.page.substr(4)
        let tpl_group = from_id.split('_')[0]
        if (!['input', 'output', 'param'].includes(tpl_group)) {
          tpl_group = 'dags'
        }
        for (let i = 0; i < this.templates_edit[tpl_name]['template'][tpl_group].length; i++) {
          if (this.templates_edit[tpl_name]['template'][tpl_group][i].id === from_id) {
            this.templates_edit[tpl_name]['template'][tpl_group][i].outputs = this.templates_edit[tpl_name]['template'][tpl_group][i].outputs || {}
            this.templates_edit[tpl_name]['template'][tpl_group][i].outputs[from_port] = this.templates_edit[tpl_name]['template'][tpl_group][i].outputs[from_port] || []
            this.templates_edit[tpl_name]['template'][tpl_group][i].outputs[from_port].push([to_type, to_id, to_port])
            return
          }
        }
        return;
      }
      try {
        // if (from_id.toString().indexOf(':') > 0) {
        //   from_id = from_id.toString().split(':')[1]
        // }
        // if (to_id.toString().indexOf(':') > 0) {
        //   to_id = to_id.toString().split(':')[1]
        // }
        const params = {
          from_id,
          from_port,
          to_id,
          to_type,
          to_port,
        };
        await secureFetch(`/api/dags/connections`, {
          method: "POST",
          data: params
        });
        // const newConnection = await response.json();
        // console.log('newConnection', newConnection)
      } catch (error) {
        console.error("Ошибка при добавлении связи:", error);
        messageStore.addMessage({type: "error", text: "Ошибка при добавлении связи."});
      }
    },
    //
    async deleteConnection(connectionData) {
      console.log('deleteConnection', connectionData)
      if (this.page.substr(0, 4) === 'tpl:') {
        const tpl_name = this.page.substr(4)
        let tpl_group = connectionData.source.split('_')[0]
        if (!['input', 'output', 'param'].includes(tpl_group)) {
          tpl_group = 'dags'
        }
        if (!this.templates_edit[tpl_name]['template'][tpl_group]) {
          console.log('deleteConnection', 'some error')
          return
        }
        let sourceHandle = connectionData.sourceHandle.split('_')
        for (let i = 0; i < this.templates_edit[tpl_name]['template'][tpl_group].length; i++) {
          if (this.templates_edit[tpl_name]['template'][tpl_group][i].id === connectionData.source) {
            this.templates_edit[tpl_name]['template'][tpl_group][i].outputs[sourceHandle[1]] = this.templates_edit[tpl_name]['template'][tpl_group][i].outputs[sourceHandle[1]].filter((conn) => conn[1] !== connectionData.target)
            return
          }
        }
        return
      } else {
        if (!this.get_dag(connectionData.source) || !this.get_dag(connectionData.target)) {
          return
        }
      }
      const messageStore = useMessageStore();
      try {
        let targetHandle = connectionData.targetHandle.split('_')
        targetHandle = [targetHandle[0], targetHandle.slice(1).join('_')]

        let url = [
          '/api/dags/connections',
          connectionData.source,
          connectionData.sourceHandle.split('_')[1],
          targetHandle[0],
          connectionData.target,
          targetHandle[1]].join('/');

        await secureFetch(url,
          {method: "DELETE"});
      } catch (error) {
        console.error("Ошибка при удалении связи:", error);
        messageStore.addMessage({type: "error", text: "Ошибка при удалении связи."});
      }
    },
    async add_template(template) {
      const messageStore = useMessageStore();
      try {
        const response = await secureFetch(`/api/templates`, {
          method: "POST",
          data: template
        });
        const answer = await response.json();
        if (answer.code !== 'ok') {
          messageStore.addMessage({type: answer.code, text: answer.message});
        }

      } catch (error) {
        console.error("Ошибка при добавлении шаблона:", error);
        messageStore.addMessage({type: "error", text: "Ошибка при добавлении шаблона."});
      }
    },
    async set_params({id, params, page, group}) {
      // console.log('store set_params', id, params, page, group)
      const messageStore = useMessageStore();
      if (page.substr(0, 4) === 'tpl:') {
        const tpl_name = page.substr(4)
        if (!['input', 'output', 'param'].includes(group)) {
          group = 'dags'
        }
        for (let i = 0; i < this.templates_edit[tpl_name]['template'][group].length; i++) {
          if (this.templates_edit[tpl_name]['template'][group][i].id === id) {
            for (let key in params) {
              if (group !== 'dags' && key[0] === '_') {
                this.templates_edit[tpl_name]['template'][group][i][key.substr(1)] = params[key]
                continue
              }
              this.templates_edit[tpl_name]['template'][group][i].params = this.templates_edit[tpl_name]['template'][group][i].params || {}
              this.templates_edit[tpl_name]['template'][group][i].params[key] = params[key]
            }
            // this.templates_edit[tpl_name]['template'][group][i].params = params
            return
          }
        }
        return
      }
      try {
        await secureFetch(`/api/dags/${id}/params`, {
          method: "POST",
          data: {params}
        });
      } catch (error) {
        console.error("Ошибка при установке параметров:", error);
        messageStore.addMessage({type: "error", text: "Ошибка при установке параметров."});
      }
    },
    async template_save(index) {
      const messageStore = useMessageStore();
      const tpl_key = this.page.substr(4)
      const [tpl_name, version] = tpl_key.split('|')
      if (this.templates_edit[tpl_key].on_save || !this.templates_edit[tpl_key].need_save) {
        messageStore.addMessage({type: "info", text: "Template already saved."});
        return
      }
      this.templates_edit[tpl_key].on_save = true
      try {
        const data_keys = ['sub_title', 'description', 'template']

        let data = {}
        for (let key of data_keys) {
          if (this.templates_edit[tpl_key][key]) {
            data[key] = this.templates_edit[tpl_key][key]
          }
        }
        const response = await secureFetch(`/api/templates/save`, {
          method: "POST",
          data: {
            name: tpl_name,
            version,
            ...data
          }
        });
        const answer = await response.json();
        this.templates_edit[tpl_key].on_save = false
        if (answer.code !== 'ok') {
          messageStore.addMessage({type: answer.code, text: answer.message});
        } else {
          this.templates_edit[tpl_key].need_save = false
        }
      } catch (error) {
        console.error("Ошибка при сохранении шаблона:", error);
        messageStore.addMessage({type: "error", text: "Ошибка при сохранении шаблона."});
        this.templates_edit[tpl_key].on_save = false
      }
    },
    // Инициализация
    async initialize() {
      if (!this.initialized) {
        await this.fetchInitialData();
        this.setupWebSocket();
        this.initialized = true;
      }
    },
    getDagByName(template) {
      for (let i = 0; i < this.dags_db.length; i++) {
        if (this.dags_db[i].name === template) {
          return this.dags_db[i]
        }
      }
      return {}
    },
    get_template(name, version) {
      for (let i = 0; i < this.templates.length; i++) {
        if (this.templates[i].name === name && this.templates[i].version === version) {
          return this.templates[i]
        }
      }
      return {}
    },
    get_pin(name) {
      for (let i = 0; i < this.pins_db.length; i++) {
        if (this.pins_db[i].name === name) {
          return this.pins_db[i]
        }
      }
      return {}
    },
    async save_dags() {
      //   get: /api/orchestrator/save
      await secureFetch(`/api/orchestrator/save`, {
        method: "GET",
      }).then(response => {
        console.log('save_dags', response)
        const messageStore = useMessageStore();
        if (response.ok) {
          messageStore.addMessage({type: "success", text: "Dags saved."});
          return response;
        } else {
          messageStore.addMessage({type: "error", text: "Dags not saved."});
        }
      });

    }
  },
  getters: {
    getDagById: (state) => (id) => state.dags.find((dag) => dag.id === id),
  },
});

export default useDagsStore;
