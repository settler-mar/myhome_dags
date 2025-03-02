<template>
  <v-container>
    <v-card>
      <v-data-table
        fixed-header
        multi-sort
        :headers="headers"
        :items="items"
        class="elevation-1"
      >
        <template v-slot:top>
          <v-toolbar
            flat
          >
            <v-toolbar-title>{{ pageTitle }}</v-toolbar-title>
            <v-spacer></v-spacer>

            <v-menu offset-y>
              <template v-slot:activator="{ props }">
                <v-btn v-bind="props" icon="mdi-cog"></v-btn>
              </template>
              <v-card>
                <v-card-text>
                  <v-list density="compact" id="columns_control">
                    <v-list-subheader>Columns</v-list-subheader>
                    <draggable v-model="columns">
                      <transition-group>
                        <v-list-item
                          v-for="element in columns" :key="element.id"
                          :value="element"
                          color="primary"
                        >
                          <template v-slot:prepend>
                            <v-switch :label="element.title" v-model="element.show" hide-details @click.stop/>
                          </template>
                        </v-list-item>
                      </transition-group>
                    </draggable>
                  </v-list>
                </v-card-text>
              </v-card>
            </v-menu>
            <v-btn
              color="blue-darken-1"
              @click="loadTableData"
            >text
            </v-btn>

            <v-dialog v-model="dialogDelete" max-width="500px">
              <v-card>
                <v-card-title class="text-h5">Are you sure you want to delete this item?</v-card-title>
                <v-card-actions>
                  <v-spacer></v-spacer>
                  <v-btn color="blue-darken-1" variant="text" @click="closeDelete">Cancel</v-btn>
                  <v-btn color="blue-darken-1" variant="text" @click="deleteItemConfirm">OK</v-btn>
                  <v-spacer></v-spacer>
                </v-card-actions>
              </v-card>
            </v-dialog>
          </v-toolbar>
        </template>
        <template v-slot:item="{ item }">
          <tr>
            <td v-for="column in headers" :key="column.key">
              {{ item[column.key] }}
            </td>
          </tr>
        </template>
      </v-data-table>
    </v-card>
  </v-container>
</template>

<script>
import tablesStore from "@/store/tables";
import {mapStores} from "pinia";
// import messagesStore from "@/store/messages";
import {secureFetch} from "@/services/fetch";
import Null from "axios/unsafe/helpers/null";
import {VueDraggableNext} from 'vue-draggable-next'

export default {
  data() {
    return {
      _columns: Null,
      dialogDelete: false,
      has_set_password: false,
    }
  },
  components: {
    draggable: VueDraggableNext,
  },
  computed: {
    pageTitle() {
      return this.$route.meta.title || 'Таблица'
    },
    table() {
      return this.$route.meta.tableModel
    },
    items() {
      if (!this.tablesStore.tables[this.table]) {
        return []
      }
      return this.tablesStore.tables[this.table]['items'] || []
    },
    permissions() {
      if (!this.tablesStore.tables[this.table]) {
        return {}
      }
      return this.tablesStore.tables[this.table]['permissions'] || {}
    },
    structure() {
      if (!this.tablesStore.tables[this.table]) {
        return []
      }
      let struct = this.tablesStore.tables[this.table]['structure'] || []

      // if (this.permissions['can_edit'] && !this.has_set_password) {
      //   struct.push({name: 'password', align: 'center'})
      // }
      let root = this
      return struct.filter(item => {
        if (item.name === 'password') {
          root.has_set_password = true
          return false
        }
        return true
      })
    },
    headers() {
      if (!this.columns) {
        return []
      }
      return this.columns.filter(column => column.show)
    },
    columns: {
      get() {
        if (!this._columns) {
          this._columns = this.structure.map(item => {
            return {
              id: item.name,
              title: item.name,
              key: item.name,
              align: item.align || 'left',
              sortable: item.sortable || true,
              show: true
            }
          })
        }
        return this._columns
      },
      set(value) {
        this._columns = value
      }
    },
    ...mapStores(tablesStore)
  },
  created() {
    this.loadTableData()
  },
  methods: {
    closeDelete() {
      this.dialogDelete = false
    },
    deleteItemConfirm() {
      this.dialogDelete = false
      console.log('deleteItemConfirm')
    },
    loadTableData() {
      if (!this.$route.meta.tableModel) {
        return
      }
      this.tablesStore.loadTableData(this.$route.meta.tableModel)
    }
  },
  watch: {
    tablesStore: {
      handler() {
        this._columns = null
      },
      deep: true
    }
  }
}
</script>

