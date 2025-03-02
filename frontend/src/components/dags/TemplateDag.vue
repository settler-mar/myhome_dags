<template>

  <div class="nodes">
    <v-dialog max-width="500">
      <template v-slot:activator="{ props: activatorProps }">
        <v-btn
          v-bind="activatorProps"
          color="surface-variant"
          text="New template"
          variant="flat"
          @click="add_template">
          New template
        </v-btn>
      </template>

      <template v-slot:default="{ isActive }">
        <v-card title="New template">
          <v-text-field
            v-model="template.name"
            label="Name"
          ></v-text-field>
          <v-text-field
            v-model="template.description"
            label="Description"
          ></v-text-field>
          <v-text-field
            v-model="template.sub_title"
            label="Sub Title"
          ></v-text-field>
          <v-text-field
            v-model="template.version"
            label="Version"
          ></v-text-field>

          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn
              text="Save"
              @click="isActive.value = false; create_template()"
            ></v-btn>
            <v-btn
              text="Close"
              @click="isActive.value = false"
            ></v-btn>
          </v-card-actions>
        </v-card>
      </template>
    </v-dialog>

    <div class="vue-flow__node-default" v-for="dag in template_collect"
         width="100%"
         :key="dag.id"
         :tooltip="dag.description"
         :draggable="!dagsStore.templates_edit['tpl:' + dag.name + '|' + dag.version]"
         @dragstart="onDragStart($event, get_dag(dag))"
         @mousedown="set_tooltip_show($event, false)"
    >
      {{ dag.name }}
      <span v-if="dag.versions.length === 1" class="version">&nbsp;&nbsp;v{{ dag.version }}</span>
      <select v-else class="version" v-model="dag.version">
        <option v-for="version in dag.versions"
                :key="version" :value="version">
          v{{ version }}
        </option>
      </select>

      <div class="button-blk">
        <v-dialog max-width="500">
          <template v-slot:activator="{ props: activatorProps }">
            <v-btn
              v-bind="activatorProps"
              icon
              size="x-small"
              @click="copy_template(dag)">
              <v-icon>mdi-content-copy</v-icon>
            </v-btn>
          </template>

          <template v-slot:default="{ isActive }">
            <v-card>
              <v-card-title>New version</v-card-title>
              <v-card-text>
                <v-text-field
                  v-model="template.version"
                  label="Version"
                ></v-text-field>
              </v-card-text>
              <v-card-text>
                <v-btn text @click="isActive.value = false; create_template()">Copy</v-btn>
                <v-btn text @click="isActive.value = false">Cancel</v-btn>
              </v-card-text>
            </v-card>
          </template>
        </v-dialog>
        <v-btn icon size="x-small" v-if="1" @click="open_tpl(dag, true)">
          <v-icon>mdi-pencil</v-icon>
        </v-btn>
        <v-btn icon size="x-small" v-else @click="open_tpl(dag,false)">
          <v-icon>mdi-eye</v-icon>
        </v-btn>
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
      isActive: false
    }
  },
  computed: {
    template_collect() {
      let templates = {}
      for (let template of this.dagsStore.templates) {
        if (!templates[template.name]) {
          templates[template.name] = {...template}
          templates[template.name].versions = []
        }
        templates[template.name].version = template.version
        templates[template.name].versions.push(template.version)
      }
      // console.log(Object.values(templates))
      return Object.values(templates);
    },
    ...mapStores(dagsStore)
  },
  methods: {
    create_template() {
      this.dagsStore.add_template(this.template)
      // console.log(this.template)
    },
    set_tooltip_show(event, show) {
      let el = event.srcElement
      if (show) {
        el.classList.remove('on_dnd')
      } else {
        el.classList.add('on_dnd')
      }
    },
    add_template() {
      this.template = {
        name: 'New template',
        description: 'Some description',
        sub_title: 'Sub title',
        version: '0.0.1',
      }
    },
    copy_template(dag) {
      const tpl = this.dagsStore.get_template(dag.name, dag.version)
      this.template = {...tpl}
    },
    open_tpl(dag, edit) {
      const page_id = dag.name + '|' + dag.version
      const tpl = this.dagsStore.get_template(dag.name, dag.version)
      root.dagsStore.templates_edit[page_id] = {
        title: dag.name + ' v' + dag.version,
        ...tpl,
        need_save: false,
      }
      this.dagsStore.page = 'tpl:' + page_id
    },
    get_dag(dag) {
      console.log(dag)
      return {
        name: 'tpl:' + dag.name + '|' + dag.version,
        type: 'dag',
      }
    },
    onDragStart
  },
  mounted() {
    root = this
  }
}
</script>
