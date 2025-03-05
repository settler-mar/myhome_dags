<!-- HomePage, Notes list -->
<template>
  <!--    {{ nodes }}-->
  <!--  {{ edges }}-->
  <!--  {{ dagsStore.dags_db}}-->
  <!--  {{ edited_params }}-->
  <!--  {{ sel_el }}-->
  <!--  {{dagsStore.templates_edit[this.dagsStore.page.substr(4)]['input']}}-->
  <v-container style="max-width: 1900px; height: 100%" class="dnd-flow" @drop="onDrop">
    <VueFlow
      :nodes="nodes"
      :edges="edges"
      :class="{ dark }"
      class="basic-flow"
      :snap-to-grid="true"
      :default-viewport="{ zoom: 1.5 }"
      :min-zoom="0.2"
      :max-zoom="4"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      ref="flow"
      fit-view-on-init
      :applyDefault="true"
      @nodes-change="onChangeNode"
      @edges-change="onChangeEdge"
      @connect="onConnect"
    >
      <DropzoneBackground
        :style="{
          backgroundColor: isDragOver ? '#878787' : 'transparent',
          transition: 'background-color 0.2s ease',
          color: '#eee',
          textShadow: '0 0 5px 1px #000',
          fontSize: '2.5rem',
          // zIndex:99999,
        }"
      >
        <p v-if="isDragOver">Drop here</p>
      </DropzoneBackground>

      <Background pattern-color="#aaa" :gap="15"/>

      <!--      <MiniMap/>-->

      <Controls position="bottom-center">
        <!--        <ControlButton title="Reset Transform" @click="resetTransform">-->
        <!--          <Icons name="reset"/>-->
        <!--        </ControlButton>-->

        <ControlButton title="Shuffle Node Positions">
          <Icons name="update"/>
        </ControlButton>

        <ControlButton title="Toggle Dark Mode" @click="toggleDarkMode">
          <Icons v-if="dark" name="sun"/>
          <Icons v-else name="moon"/>
        </ControlButton>
        <!--        <ControlButton title="Log `toObject`" @click="logToObject">-->
        <!--          <Icons name="log"/>-->
        <!--        </ControlButton>-->
      </Controls>
      <controls position="top-left" :showZoom="false" :showFitView="false" :showInteractive="false">
        <v-col cols="auto">
          <v-btn density="compact" icon="mdi-package-down" height="52" width="52" @click="save_dags"></v-btn>
        </v-col>
        <tabs
          v-model:model="dagsStore.page"
          :list="pages"
          :add_button="add_page"
          :on_close="close_tab"
          :on_save="save_tab"
        />
      </controls>

      <!-- bind your custom node type to a component by using slots, slot names are always `node-<type>` -->
      <template #node-special="specialNodeProps">
        <SpecialNode v-bind="specialNodeProps"/>
      </template>

      <!-- bind your custom edge type to a component by using slots, slot names are always `edge-<type>` -->
      <template #edge-special="specialEdgeProps">
        <SpecialEdge v-bind="specialEdgeProps"/>
      </template>
    </VueFlow>

    <aside>
      <template v-if="sel_el && !Object.is(sel_el)">
        <input type="radio" id="item0" name="select_tab">
        <label for="item0">Property</label>
        <EditDagParam :params="edited_params"/>
      </template>

      <input type="radio" checked id="item4" name="select_tab">
      <label for="item4">Pins</label>
      <PinsDag/>

      <input type="radio" checked id="item1" name="select_tab">
      <label for="item1">Dags</label>
      <SidebarDag/>

      <input type="radio" id="item2" name="select_tab">
      <label for="item2">Templates</label>
      <TemplateDag/>

      <template v-if="dagsStore.page.substr(0,4)==='tpl:'">
        <input type="radio" id="item3" name="select_tab">
        <label for="item3">Template property</label>
        <TemplateProperty/>
      </template>
      <div/>
    </aside>
  </v-container>
</template>

<script>
import {ref} from 'vue'
import {VueFlow, useVueFlow} from '@vue-flow/core'
import {Background} from "@vue-flow/background";
import {MiniMap} from "@vue-flow/minimap";
import {Controls, ControlButton} from "@vue-flow/controls";
import Tabs from "@/components/dags/tabs.vue";

// these are our nodes
const {addEdges, screenToFlowCoordinate} = useVueFlow()

const {onDragOver, onDrop, onDragLeave, isDragOver, dndInit} = useDragAndDrop()


// custom node component
import SpecialNode from '@/components/dags/SpecialNode.vue'
import SpecialEdge from '@/components/dags/SpecialEdge.vue'
import Icons from '@/components/Icons.vue'
import SidebarDag from '@/components/dags/SidebarDag.vue'
import PinsDag from '@/components/dags/PinsDag.vue'
import TemplateDag from '@/components/dags/TemplateDag.vue'
import TemplateProperty from '@/components/dags/TemplateProperty.vue'
import useDragAndDrop from '@/module/useDnD.js'
import DropzoneBackground from '@/components/dags/DropzoneBackground.vue'
import EditDagParam from "@/components/dags/EditDagParam.vue";

import dagsStore from "@/store/dags";
import messagesStore from "@/store/messages";
import {mapStores} from "pinia";

let flow = null

export default {
  data() {
    return {
      dark: true,
      isDragOver: ref(isDragOver),
      lastAction: null,
      // tab: 'main',
      las_tab_change: null,
      edited_params: [],
      prev_params: {},
      params_set_timer: null, // [timer_id, dag_id, page_id]
    }
  },
  components: {
    VueFlow,
    SpecialNode,
    SpecialEdge,
    Background,
    MiniMap,
    Controls,
    ControlButton,
    Icons,
    PinsDag,
    SidebarDag,
    TemplateDag,
    TemplateProperty,
    DropzoneBackground,
    Tabs,
    EditDagParam,
  },
  computed: {
    nodes() {
      if (this.dagsStore.page.substr(0, 4) === 'tpl:') {
        let nodes = []
        let tpl_key = this.dagsStore.page.substr(4)
        for (let group of ['input', 'param', 'output', 'dags']) {
          for (let dag of this.dagsStore.templates_edit[tpl_key]['template'][group] || []) {
            let sub_title = dag['sub_title']
            let params = dag['params'] || {}
            let pins = {}
            if (group === 'dags') {
              sub_title = []
              params = {}
              const base_dag = this.dagsStore.getDagByName(dag.name)
              for (let param of base_dag.params) {
                let value = dag.params[param.name] || param.default
                sub_title.push(`${param.name}: ${value}`)
                params[param.name] = value
              }
              // for (let key in dag.params) {
              //   sub_title.push(`${key}: ${dag.params[key]}`)
              //   params[key] = dag.params[key]
              // }
              sub_title = base_dag && base_dag.sub_title ? base_dag.sub_title : sub_title.join(', ')
            } else {
              pins[dag.group === 'output' ? 'inputs' : 'outputs'] = [{'name': 'default'}]
            }

            nodes.push({
              id: dag.id,
              type: 'special',
              position: {x: dag.position[0], y: dag.position[1]},
              data: {
                'dag': {
                  'title': dag.name,
                  ...dag,
                  'sub_title': sub_title,
                  params,
                },
                pins
              },
            })
          }
        }
        return nodes
      }/**/
      /*if (this.dagsStore.page.substr(0, 4) === 'pin:'){
        let nodes = []
        let tpl_key = this.dagsStore.page.substr(4)
        this.dagsStore
      }*/
      return this.dagsStore.dags.filter(dag => (!dag.page && this.dagsStore.page === 'main') || dag.page === this.dagsStore.page).map(dag => {
        return {
          id: dag.id,
          type: 'special',
          position: {x: dag.position[0], y: dag.position[1]},
          data: {dag},
        }
      })
    },
    edges() {
      let edges = []
      if (this.dagsStore.page.substr(0, 4) === 'tpl:') {
        const tpl_key = this.dagsStore.page.substr(4)
        for (let group_name of ['input', 'param', 'dags']) {
          for (let dag of this.dagsStore.templates_edit[tpl_key]['template'][group_name] || []) {
            if (!dag.outputs) {
              continue
            }
            for (let [key, edge] of Object.entries(dag.outputs)) {
              for (let [index, value] of edge.entries()) {
                edges.push({
                  id: `${dag.id}_${key}_${index}`,
                  source: dag.id.toString(),
                  sourceHandle: 'out_' + key,
                  target: value[1].toString(),
                  targetHandle: `${value[0]}_${value[2]}`,
                })
              }
            }
          }
        }
        return edges
      }
      for (let dag of this.dagsStore.dags) {
        if ((dag.page && dag.page !== this.dagsStore.page) || (!dag.page && this.dagsStore.page !== 'main')) {
          continue
        }
        for (let [key, value] of Object.entries(dag.outputs)) {
          for (let [index, edge] of value.entries()) {
            edges.push({
              id: `${dag.id}_${key}_${index}`,
              source: dag.id.toString(),
              sourceHandle: 'out_' + key,
              target: edge[1].toString(),
              targetHandle: `${edge[0]}_${edge[2]}`,
            })
          }
        }
      }
      return edges
    },
    pages() {
      let pages = this.dagsStore.page_collect
      for (let dag of this.dagsStore.dags) {
        let page_name = dag.page || 'main'
        if (pages.indexOf(page_name) === -1)
          pages.push(page_name)
      }
      for (let key in this.dagsStore.templates_edit) {
        pages.push({
          title: this.dagsStore.templates_edit[key].title,
          id: 'tpl:' + key,
          close: true,
          save: this.dagsStore.templates_edit[key].need_save,
          on_save: this.dagsStore.templates_edit[key].on_save,
        })
      }
      return pages
    },
    selectTPL() {
      this.las_tab_change = new Date()
      if (this.dagsStore.page.substr(0, 4) !== 'tpl:') {
        return {}
      }
      return this.dagsStore.templates_edit[this.dagsStore.page.substr(4)] || {}
    },
    tab() {
      return this.dagsStore.page
    },
    sel_el() {
      if (!flow) {
        return this.dagsStore.select_node
      }
      let sel_node = flow.getSelectedNodes ? flow.getSelectedNodes[0] : null
      if (sel_node) {
        let params = []

        let group = 'dag'
        if (this.tab.substr(0, 4) === 'tpl:') {
          group = sel_node.id.split('_')[0]
          if (['input', 'param', 'output'].indexOf(group) === -1) {
            group = 'dag'
          }
        }
        console.log('sel_el', group, sel_node)
        if (group === 'dag') {
          const base_params = {}
          let source_params = []
          if (typeof sel_node.data.dag.id === 'string' && sel_node.data.dag.id.split(':')[0] === 'tpl') {
            const tpl = this.dagsStore.get_template(sel_node.data.dag.name, sel_node.data.dag.version)
            if (!tpl) return
            for (let param of (tpl.template.param || [])) {
              base_params[param.name] = {
                ...param,
                ...param.params
              }
            }
          } else {
            for (let param of this.dagsStore.getDagByName(sel_node.data.dag.name)['params'] || []) {
              base_params[param.name] = param
            }
          }


          for (let key in sel_node.data.dag.params) {
            let param = {
              name: key,
              value: sel_node.data.dag.params[key],
            }
            if (base_params[key]) {
              param = {
                ...base_params[key],
                ...param
              }
            }
            params.push(param)
          }
        } else {
          params.push({
            'name': '_desscription',
            'description': 'Description',
            'value': sel_node.data.dag.description,
          })
          params.push({
            'name': '_name',
            'description': 'Name',
            'value': sel_node.data.dag.name,
          })
          if (group === 'param') {
            params.push({
              'name': '_public',
              'description': 'public',
              'value': sel_node.data.dag.public,
              'type': 'bool'
            })
            params.push({
              'name': 'default',
              'description': 'default value',
              'value': sel_node.data.dag.params.default,
              'type': sel_node.data.dag.params.type || 'text'
            })
            params.push({
              'name': 'type',
              'description': 'Params type',
              'value': sel_node.data.dag.params.type || 'text',
              'type': 'select',
              'items': ['text', 'int', 'float', 'bool', 'select']
            })
            if (sel_node.data.dag.params.type === 'select') {
              params.push({
                'name': 'items',
                'description': 'Items',
                'value': sel_node.data.dag.params.items || [],
                'type': 'list'
              })
            }
            if (['int', 'float'].indexOf(sel_node.data.dag.params.type) !== -1) {
              params.push({
                'name': 'min',
                'description': 'Min value',
                'value': sel_node.data.dag.params.min,
                'type': sel_node.data.dag.params.type
              })
              params.push({
                'name': 'max',
                'description': 'Max value',
                'value': sel_node.data.dag.params.max,
                'type': sel_node.data.dag.params.type
              })
              params.push({
                'name': 'step',
                'description': 'Step',
                'value': sel_node.data.dag.params.step,
                'type': sel_node.data.dag.params.type
              })
              params.push({
                'name': 'unit',
                'description': 'Unit',
                'value': sel_node.data.dag.params.unit,
                'type': 'text'
              })
            }
          }
        }
        this.edited_params = params
        this.prev_params = {
          params: JSON.parse(JSON.stringify(params)),
          id: sel_node.id,
          group,
          page: this.tab
        }
        return sel_node.data.dag
      }
      return
    },
    ...mapStores(dagsStore),
    ...mapStores(messagesStore)
  },
  methods: {
    onDrop,
    onDragOver,
    onDragLeave,
    addEdges,
    screenToFlowCoordinate,
    dndInit,
    save_dags() {
      this.dagsStore.save_dags()
    },
    toggleDarkMode() {
      this.dark = !this.dark
    },
    onChangeEdge(edges) {
      for (const edge of edges) {
        if (edge.type === 'select') {
          //skip
          continue
        } else if (edge.type === "remove") {
          this.dagsStore.deleteConnection({
            source: edge.source,
            sourceHandle: edge.sourceHandle,
            target: edge.target,
            targetHandle: edge.targetHandle
          })
          continue;
        }
        console.log('onChangeEdge', edge)
      }
    },
    onConnect(params) {
      let index_list = ['source', 'target']
      if (params['sourceHandle'].split('_')[0] !== 'out') {
        index_list = ['target', 'source']
      }

      function split_handle(handle) {
        let data = handle.split('_')
        return [data[0], data.slice(1).join('_')]
      }

      let data = [params[index_list[0]],
        ...split_handle(params[index_list[0] + 'Handle']),
        params[index_list[1]],
        ...split_handle(params[index_list[1] + 'Handle'])
      ]

      if (data[1] !== 'out' || data[4] === 'out') {
        this.messagesStore.addMessage({type: 'error', message: 'invalid connection'})
        return
      }
      this.dagsStore.addConnection(...data)
    },
    onChangeNode(changes) {
      // changes are arrays of type `NodeChange`
      for (const change of changes) {
        if (['select'].indexOf(change.type) > -1) {
          this.dagsStore.select_node = change.selected ? change.id : this.dagsStore.select_node === change.id ? null : this.dagsStore.select_node
        } else if (change.type === 'position') {
          if (change.position) {
            this.lastAction = {
              id: change.id,
              data: {position: [Math.round(change.position.x), Math.round(change.position.y)]}
            }
          } else {
            this.dagsStore.updateDag(change.id, this.lastAction.data)
          }
        } else if (change.type === 'remove') {
          this.dagsStore.removeDag(change.id)
        } else {
          console.log(change)
        }
      }
    },
    add_page() {
      let page_name = prompt('Enter page name')
      if (page_name) {
        this.dagsStore.page_collect.push({'title': page_name, 'close': true})
        this.dagsStore.page = page_name
      }
    },
    close_tab(index) {
      if (this.dagsStore.page.substr(0, 4) === 'tpl:') {
        delete this.dagsStore.templates_edit[this.dagsStore.page.substr(4)]
      } else {
        this.dagsStore.page_collect = this.dagsStore.page_collect.filter((item, i) => (item.id || item.title) !== index)
      }
      this.dagsStore.page = 'main'
    },
    save_tab(index) {
      this.dagsStore.template_save(index)
    },
    save_param(differences, id, page, group) {
      this.dagsStore.set_params({id, params: differences, page, group})
    }
  },
  watch: {
    tab(val) {
      this.dagsStore.select_node = null
      // Fit View
      // zoom out
      setTimeout(this.$refs.flow.fitView, 200)
      // this.$refs.flow.zoom
    },
    selectTPL: {
      handler: function (val) {
        if (new Date() - this.las_tab_change < 500) {
          return
        }
        console.log('time after tab change', new Date() - this.las_tab_change)
        if (val.pr_need_save === true && val.need_save === false) {
          this.las_tab_change = new Date() - -500
          this.selectTPL.pr_need_save = val.need_save
          return;
        }
        this.selectTPL.pr_need_save = val.need_save
        if (!this.selectTPL.need_save)
          this.selectTPL.need_save = true
      },
      deep: true
    },
    edited_params: {
      handler: function (val) {
        const map1 = new Map(this.prev_params.params.map(item => [item.name, item.value]));
        const differences = {};

        val.forEach(item => {
          if (map1.has(item.name) && map1.get(item.name) !== item.value) {
            differences[item.name] = item.value;
          }
        });

        if (this.params_set_timer &&
          this.params_set_timer.id === this.prev_params.id &&
          this.params_set_timer.page === this.prev_params.page) {
          clearTimeout(this.params_set_timer.timer)
        }
        if (Object.keys(differences).length === 0) {
          return
        }
        let timer = setTimeout(this.save_param, 500,
          differences, this.prev_params.id, this.prev_params.page, this.prev_params.group)
        this.params_set_timer = {
          id: this.prev_params.id,
          page: this.prev_params.page,
          timer
        }
      },
      deep: true
    }
  },
  mounted() {
    this.dagsStore.initialize()
    this.dndInit(this.$refs.flow)
    flow = this.$refs.flow
    // this.dagsStore.setPage(this.dagsStore.page)
  },
}
</script>

<style lang="scss">
/* import the necessary styles for Vue Flow to work */
@import '@vue-flow/core/dist/style.css';

/* import the default theme, this is optional but generally recommended */
@import '@vue-flow/core/dist/theme-default.css';

.vue-flow__node-param {
  --vf-node-color: var(--vf-node-color, #08ff00);
  --vf-handle: var(--vf-node-color, #08ff00);
  --vf-box-shadow: var(--vf-node-color, #08ff00);

  background: var(--vf-node-bg);
  border-color: var(--vf-node-color, #08ff00);
}

#app {
  margin: 0;
  height: 100%;
}

#app {
  text-transform: uppercase;
  font-family: 'JetBrains Mono', monospace;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
}

.vue-flow__minimap {
  transform: scale(75%);
  transform-origin: bottom right;
}

.basic-flow.dark {
  background: #2d3748;
  color: #fffffb
}

.basic-flow.dark .vue-flow__node {
  background: #4a5568;
  color: #fffffb
}

.basic-flow.dark .vue-flow__node.selected {
  background: #333;
  box-shadow: 0 0 0 2px #2563eb
}

.basic-flow .vue-flow__controls {
  display: flex;
  flex-wrap: wrap;
  justify-content: center
}

.basic-flow.dark .vue-flow__controls {
  //border: 1px solid #FFFFFB
}

.basic-flow .vue-flow__controls .vue-flow__controls-button {
  border: none;
  border-right: 1px solid #eee;
  height: 32px;
  width: 32px;
  margin-right: 2px;
}

.basic-flow .vue-flow__controls .vue-flow__controls-button svg {
  height: 100%;
  width: 100%
}

.basic-flow.dark .vue-flow__controls .vue-flow__controls-button {
  background: #333;
  fill: #fffffb;
  border: none
}

.basic-flow.dark .vue-flow__controls .vue-flow__controls-button:hover {
  background: #4d4d4d
}

.basic-flow.dark .vue-flow__edge-textbg {
  fill: #292524
}

.basic-flow.dark .vue-flow__edge-text {
  fill: #fffffb
}

.vue-flow__handle {
  border-radius: 3px;
  width: 12px;
}

.dnd-flow {
  flex-direction: column;
  display: flex;
  height: 100%
}

.dnd-flow aside {
  color: #fff;
  font-weight: 700;
  border-right: 1px solid #eee;
  padding: 15px 10px;
  font-size: 12px;
  background: #10b981bf;
  -webkit-box-shadow: 0px 5px 10px 0px rgba(0, 0, 0, .3);
  box-shadow: 0 5px 10px #0000004d
}

.dnd-flow aside .nodes > div {
  margin-bottom: 10px;
  cursor: grab;
  font-weight: 500;
  -webkit-box-shadow: 5px 5px 10px 2px rgba(0, 0, 0, .25);
  box-shadow: 5px 5px 10px 2px #00000040;
  width: 100%;
  display: flex;
  align-items: baseline;
  justify-items: baseline;

  select {
    margin: 0 3px;
    -webkit-appearance: auto;
    background: #f0f0f0;
    border: 1px solid #ccc;
  }

  .button-blk {
    display: flex;
    flex-grow: 2;
    justify-content: end;
  }
}

.dnd-flow aside .description {
  margin-bottom: 10px
}

.dnd-flow .vue-flow-wrapper {
  flex-grow: 1;
  height: 100%
}

@media screen and (min-width: 640px) {
  .dnd-flow {
    flex-direction: row
  }

  .dnd-flow aside {
    min-width: 25%
  }
}

@media screen and (max-width: 639px) {
  .dnd-flow aside .nodes {
    display: flex;
    flex-direction: row;
    gap: 5px
  }
}

.dropzone-background {
  position: relative;
  height: 100%;
  width: 100%
}

.dropzone-background .overlay {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  pointer-events: none
}

.nodrag {
  cursor: auto;
}

aside {
  display: flex;
  flex-direction: column;
  padding: 0;

  & > input[type="radio"] {
    display: none;
  }

  & > label {
    margin: 0;
    display: inline-block;
    padding: 10px 20px;
    cursor: pointer;
    border: 2px solid #ccc;
    border-radius: 5px;
    background-color: #f0f0f0;
    transition: all 0.3s;
    position: relative;
    color: #000;

    + div {
      transition: all 0.8s;
      padding: 0 5px;
      overflow: hidden;
      max-height: 0;
      flex-grow: 2;
    }

    &:hover {
      background-color: #e0e0e0;
    }
  }

  input[type="radio"]:checked {
    + label {
      background-color: #ccc;
      border: 2px solid #000;

      + div {
        padding: 5px 5px;
        max-height: 100vh;
        overflow: auto;
      }
    }
  }
}

aside button {
  display: block;
  border: 1px solid #ccc;
  border-radius: 5px;
  box-shadow: 0 0 5px 1px #000;
  padding: 5px;
  margin: 5px 0;
  width: 100%;
  background: #f0f0f0;
  color: #000;

  &:hover {
    background: #e0e0e0;
  }
}

</style>
