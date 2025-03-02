<template>

  <div class="nodes">
    <!--      <div class="vue-flow__node-input" :draggable="true" @dragstart="onDragStart($event, 'input')">Input Node</div>-->

    <div class="vue-flow__node-default" v-for="dag in dags_collect"
         :key="dag.id"
         :tooltip="dag.description"
         :draggable="true"
         @dragstart="onDragStart($event, get_dag(dag))"
         @mousedown="set_tooltip_show($event, false)"
    >
      {{ dag.name }}
    </div>

    <!--      <div class="vue-flow__node-output" :draggable="true" @dragstart="onDragStart($event, 'output')">Output Node</div>-->
  </div>

</template>

<script>
import useDragAndDrop from '@/module/useDnD.js'

const {onDragStart} = useDragAndDrop();
import dagsStore from "@/store/dags";
import {mapStores} from "pinia";

export default {
  computed: {
    dags_collect() {
      return this.dagsStore.pins_db;
    },
    ...mapStores(dagsStore)
  },
  methods: {
    set_tooltip_show(event, show) {
      let el = event.srcElement
      if (show) {
        el.classList.remove('on_dnd')
      } else {
        el.classList.add('on_dnd')
      }
    },
    get_dag(dag) {
      console.log(dag)
      return {
        name: 'pin:' + dag.code,
        type: 'dag',
      }
    },
    onDragStart
  }
}
</script>
