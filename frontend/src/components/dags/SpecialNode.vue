<template>
  <div class="vue-flow__node-default">
    <!--        {{ data.dag.id }}-->
    <!--    {{ data.dag }}-->
    <!--    {{ config }}-->
    <!--    {{ config['params']}}-->
    <!--    {{ inputs}}-->
    <span class="dag_title" :version="version">{{ data.dag.title }}</span>
    <span class="dag_sub_title" v-if="data.dag.sub_title">{{ sub_title }}</span>
    <span class="dag_sub_title" v-if="data.dag.group">{{ data.dag.group }}</span>
    <v-btn
      class="dag_ctrl"
      size="x-small"
      density="compact"
      v-if="String(data.dag.id).split(':')[0] === 'tpl'"
      icon="mdi-eye"
      @click.stop="view_tpl(data.dag.id)"
    />

    <div class="vue-flow__handle-wrap" :item_count="inputs.length">
      <Handle
        v-for="(pin, key) in inputs"
        type="target"
        :position="pin.position"
        :tooltip="data.view_mode?null:pin.tooltip"
        :id="pin.id"
        v-bind:class="{ 'is_param':pin.id.startsWith('param_')}"
      />
    </div>

    <div class="vue-flow__handle-wrap" :item_count="outputs.length">
      <Handle
        v-for="(pin, key) in outputs"
        type="source"
        :position="pin.position"
        :tooltip="data.view_mode?null:pin.tooltip"
        :id="pin.id"
      />
    </div>
  </div>
</template>

<script>
import {mapStores} from "pinia";

import {Handle, Position} from '@vue-flow/core'
import dagsStore from "@/store/dags";

export default {
  props: {
    position: {
      type: Object,
      required: true,
    },
    data: {
      type: Object,
      required: true,
    }
  },
  data() {
    return {
      Position: Position
    }
  },
  components: {
    Handle
  },
  methods: {
    async view_tpl(id) {
      await this.dagsStore.edit_active_template(id)
    }
  },
  computed: {
    ...mapStores(dagsStore),
    config() {
      if (this.data.pins &&
        ['input', 'output', 'param'].indexOf(this.data.dag.id.split('_')[0]) !== -1) {
        return this.data.pins
      }
      if (this.data.dag.pins &&
        (['Param', 'Input', 'Output'].indexOf(this.data.dag.code) !== -1)) {
        return this.data.dag.pins
      }

      if (typeof (this.data.dag.id) === 'string' && this.data.dag.id.split(':')[0] === 'tpl') {
        const tpl = this.dagsStore.get_template(this.data.dag.name, this.data.dag.version)
        if (!tpl || !tpl.template) return {}
        return {
          inputs: tpl.template['input'] || [],
          outputs: tpl.template['output'] || [],
          params: tpl.template['param'] || []
        }
      }

      if (typeof (this.data.dag.id) === 'string' && this.data.dag.id.split(':')[0] === 'pin') {
        const tpl = this.dagsStore.get_pin(this.data.dag.name)
        if (!tpl || Object.keys(tpl).length === 0) return {}
        return tpl
      }

      for (let dag of this.dagsStore.dags_db) {
        if (dag.name === this.data.dag.name) {
          return dag
        }
      }


      console.log('skip', this.data.dag)
      return {}
    },
    version() {
      return ''
      if (this.data.dag.version) {
        return 'v' + this.data.dag.version
      }
      if (typeof this.data.dag.public !== 'undefined') {
        return this.data.dag.public ? 'public' : 'private'
      }
    },
    pos() {
      return {
        x: Math.round(this.position.x),
        y: Math.round(this.position.y)
      }
    },
    sub_title() {
      return this.data.dag.sub_title.replace(/\{([\w\s]+)\}/g, (match, key) => {
        return this.data.dag.params[key] !== undefined ? this.data.dag.params[key] : match;
      });
    },
    inputs() {
      let pins = []
      /*if (['input', 'output', 'param'].indexOf(this.config['code']) !== -1) {
        console.log('>inputs', this.config)
        return pins
      }*/
      if (!this.config.inputs && !this.config.params) {
        return pins
      }
      let need_sort = false
      for (let pin of this.config['inputs'] || []) {
        pins.push({
          id: 'in_' + pin.name,
          position: Position.Top,
          tooltip: pin.description,
          sort_pos: pin.position || [0, 0]
        })
        if (pin.position) {
          need_sort = true
        }
      }
      for (let pin of this.config['params'] || []) {
        if (pin['public'] !== false) {
          pins.push({
            id: 'param_' + pin.name,
            position: Position.Top,
            tooltip: pin.description,
            sort_pos: pin.position || [0, 0]
          })
          if (pin.position) {
            need_sort = true
          }
        }
      }
      if (need_sort) {
        pins.sort((a, b) => {
          return a.sort_pos[0] - b.sort_pos[0]
        })
      }
      return pins
    },
    outputs() {
      let pins = []
      if (!this.config.outputs) {
        return pins
      }
      for (let pin of this.config['outputs'] || []) {
        pins.push({
          id: 'out_' + pin.name,
          position: Position.Bottom,
          tooltip: pin.description
        })
      }
      return pins
    }
  },
}
</script>

<style lang="scss">
.dag_sub_title {
  display: block;
  font-size: 0.6em;
  color: #999;
  margin-top: -5px;
  text-transform: none;
}

.dag_title {
  display: block;
  font-size: 1em;
  font-weight: bold;
  color: #333;
  position: relative;

  &[version]:after { //  надстрочный текст
    content: attr(version);
    font-size: 0.4em;
    color: #999;
    margin-left: 1px;
    position: absolute;
    top: 0px;
  }
}


.vue-flow__handle-wrap {
  display: flex;
  justify-content: space-between;
  width: 100%;
}

.vue-flow__handle.is_param {
  background-color: #a6ff7a;
  border-color: #476e35;
}

@for $i from 2 through 6 {
  .vue-flow__handle-wrap[item_count="#{$i}"] {
    @for $j from 1 through $i {
      .vue-flow__handle:nth-child(#{$j}) {
        // 2: -33px +33px  (100/3)
        // 3: -25px 0 25px (100/4)
        // 4: -30px -10px 10px 30px (100/5)
        // 5: -25px -12.5px 0 12.5px 25px (100/6)
        left: calc(100% / #{$i + 1} * #{$j});
      }
    }
  }
}

.dag_ctrl {
  position: absolute;
  right: -7px;
  top: -7px;
  z-index: 1;
  padding: 0;
  height: 16px !important;
  width: 16px !important;
  background: #d5d5d5;
}
</style>
