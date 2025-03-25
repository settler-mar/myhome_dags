<template>
  <div>
    <template v-if="input.length">
      <h3>Input</h3>
      <table class="table-auto" style="min-width: 100%">
        <thead>
        <tr>
          <th>Pin</th>
          <th>Description</th>
          <th>Value</th>
          <th></th>
        </tr>
        </thead>
        <tbody>
        <tr v-for="pin in input" :key="pin.id">
          <td>{{ pin.name }}</td>
          <td>{{ pin.description }}</td>
          <td>
            {{ values['in'][pin.name]['value'] }}
            <br>
            <small>{{ values['in'][pin.name]['ts'] }}</small>
          </td>
          <td>
            <v-menu
              v-model="showPopup[pin.name]"
              :close-on-content-click="false"
              offset="0"
              location="left"
              origin="overlap"
              transition="scale-transition"
            >
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  color="primary"
                  icon
                  size="small"
                  density="compact"
                  class="rounded-circle"
                >
                  <v-icon size="20">mdi-pencil</v-icon>
                </v-btn>
              </template>

              <v-card class="pa-2" width="280">
                <!-- key заставляет пересоздать input при открытии -->
                <v-text-field
                  :key="showPopup"
                  v-model="inputValue"
                  label="Enter value"
                  autofocus
                  dense
                  hide-details
                  variant="outlined"
                  class="ma-0"
                  @keydown.enter="submitValue(pin)"
                  @keydown.esc="closePopup(pin)"
                >
                  <template #append-inner>
                    <v-btn
                      icon
                      size="small"
                      density="compact"
                      @click="submitValue(pin)"
                      color="success"
                      variant="flat"
                      class="me-1"
                    >
                      <v-icon size="18">mdi-check</v-icon>
                    </v-btn>
                    <v-btn
                      icon
                      size="small"
                      density="compact"
                      @click="closePopup(pin)"
                      color="primary"
                      variant="flat"
                    >
                      <v-icon size="18">mdi-close</v-icon>
                    </v-btn>
                  </template>
                </v-text-field>
              </v-card>
            </v-menu>
          </td>
        </tr>
        </tbody>
      </table>
      <template v-if="output.length">
        <br>
        <hr>
        <br>
      </template>
    </template>
    <template v-if="output.length">
      <h2>Output</h2>
      <table class="table-auto" style="min-width: 100%">
        <thead>
        <tr>
          <th>Pin</th>
          <th>Description</th>
          <th>Value</th>
        </tr>
        </thead>
        <tbody>
        <tr v-for="pin in output" :key="pin.id">
          <td>{{ pin.name }}</td>
          <td>{{ pin.description }}</td>
          <td>--</td>
        </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>

<script>
import {mapStores} from 'pinia';
import logsStore from '@/store/logs';
import dagsStore from '@/store/dags';
import {secureFetch} from "@/services/fetch";

export default {
  props: {
    sel_el: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      inputValue: '',
      showPopup: {},
      ts_now: Date.now() / 1000
    }
  },
  computed: {
    ...mapStores(logsStore),
    ...mapStores(dagsStore),
    config() {
      // if (this.sel_el.pins &&
      //   ['input', 'output', 'param'].indexOf(this.sel_el.id.split(':')[0]) !== -1) {
      //   return this.sel_el.pins
      // }
      if (this.sel_el.pins &&
        (['Param', 'Input', 'Output'].indexOf(this.sel_el.code) !== -1)) {
        return this.sel_el.pins
      }

      if (typeof (this.sel_el.id) === 'string' && this.sel_el.id.split(':')[0] === 'tpl') {
        const tpl = this.dagsStore.get_template(this.sel_el.name, this.sel_el.version)
        if (!tpl || !tpl.template) return {}
        return {
          inputs: tpl.template['input'] || [],
          outputs: tpl.template['output'] || [],
          params: tpl.template['param'] || []
        }
      }

      if (typeof (this.sel_el.id) === 'string' && this.sel_el.id.split(':')[0] === 'pin') {
        const tpl = this.dagsStore.get_pin(this.sel_el.name)
        if (!tpl || Object.keys(tpl).length === 0) return {}
        return tpl
      }

      for (let dag of this.dagsStore.dags_db) {
        if (dag.name === this.sel_el.name) {
          return dag
        }
      }

      console.log('skip', this.data.dag)
      return {}
    },
    output() {
      return this.config.outputs || []
    },
    input() {
      return this.config.inputs || []
    },
    values() {
      let values = {
        'in': {},
        'out': {},
        'param': {}
      }
      let base_value = this.logsStore.by_dags_ports[this.sel_el.id] || {}
      for (let pin of this.input) {
        let data = base_value['in'] && typeof base_value['in'][pin.name] === 'object' ? base_value['in'][pin.name] : {}
        values['in'][pin.name] = {
          value: data.value || '',
          ts: data.ts ? this.echoTime(data.ts) : null,
          ts_val: data.ts
        }
      }
      for (let pin of this.output) {
        let data = base_value['out'] && typeof base_value['out'][pin.name] === 'object' ? base_value['out'][pin.name] : {}
        values['out'][pin.name] = {
          value: data.value || '',
          ts: data.ts ? this.echoTime(data.ts) : null,
          ts_val: data.ts
        }
      }
      return values
    }
  },
  methods: {
    async submitValue(pin) {
      console.log('submitValue', this.inputValue, pin);
      // send value to server
      // if page start with vtpl: /api/live/dag/{tpl_id}/{dag_id}/{port_name}/set?value={value}
      // else: /api/live/dag/{dag_id}/{port_name}/set?value={value}
      let tpl_id = this.dagsStore.page.split(':')[1];
      let is_tpl = this.dagsStore.page.split(':')[0] === 'vtpl';
      let url = [
        '/api/live/dag',
        is_tpl ? tpl_id : null,
        this.sel_el.id,
        pin.name,
        'set?value=' + this.inputValue
      ].join('/').replaceAll('//', '/');
      await secureFetch(url, {method: 'POST'});
      this.inputValue = ''
      this.closePopup(pin);
    },
    closePopup(pin) {
      this.showPopup[pin.name] = false;
      // this.$refs.inputRef.blur();
      // this.$emit('update:modelValue', false);
    },
    echoTime(ts) {
      if (!ts) return '';
      const diff = this.ts_now - ts;
      if (diff < 60) return `${Math.floor(diff)}s`;
      if (diff < 3600) return `${Math.floor(diff / 60)}m${Math.floor(diff % 60)}s`;
      return `${Math.floor(diff / 3600)}h${Math.floor((diff % 3600) / 60)}m`;
    }
  },

  mounted() {
    setInterval((el) => {
      el.ts_now = Date.now() / 1000;
    }, 500, this);
  },
}
</script>


<style scoped>

</style>
