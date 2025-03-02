<template>
  <div>
    <v-text-field v-model="selectTPL.description" label="Description"></v-text-field>

    <v-text-field v-model="selectTPL.sub_title" label="Sub Title"></v-text-field>

    <!--    {{ selectTPL }}-->
    <div class="nodes">
      <div class="vue-flow__node-input" :draggable="true" @dragstart="onDragStart($event, dag_map['input'])">
        Input Node
      </div>
      <div class="vue-flow__node-default vue-flow__node-param" :draggable="true"
           @dragstart="onDragStart($event, dag_map['param'])">Param Node
      </div>

      <!--      <div class="vue-flow__node-default" v-for="dag in dags_collect"-->
      <!--           :key="dag.id"-->
      <!--           :tooltip="dag.description"-->
      <!--           :draggable="true"-->
      <!--           @dragstart="onDragStart($event, dag)"-->
      <!--           @mousedown="set_tooltip_show($event, false)"-->
      <!--      >-->
      <!--        {{ dag.name }} (v{{ dag.version }})-->
      <!--      </div>-->

      <div class="vue-flow__node-output" :draggable="true" @dragstart="onDragStart($event, dag_map['output'])">
        Output Node
      </div>
    </div>
  </div>

</template>

<script>
import useDragAndDrop from '@/module/useDnD.js'

const {onDragStart} = useDragAndDrop();
import dagsStore from "@/store/dags";
import {mapStores} from "pinia";

let root = null

export default {
  data() {
    return {
      template: {},
      isActive: false,
      dag_map: {
        input: {'name': 'tpl.input'},
        output: {'name': 'tpl.output'},
        param: {'name': 'tpl.param'}
      }
    }
  },
  computed: {
    selectTPL() {
      if (this.dagsStore.page.substr(0, 4) !== 'tpl:') {
        return {}
      }
      if (this.dagsStore.page.substr(0, 4) !== 'pin:') {
        return {}
      }
      return this.dagsStore.templates_edit[this.dagsStore.page.substr(4)] || {}
    },
    ...mapStores(dagsStore)
  },
  methods: {
    onDragStart
  },
  mounted() {
    root = this
  }
}
</script>
