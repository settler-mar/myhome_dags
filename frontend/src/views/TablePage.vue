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
          <v-toolbar flat>
            <v-toolbar-title>{{ pageTitle }}</v-toolbar-title>
            <v-spacer></v-spacer>

            <v-btn icon="mdi-refresh" @click="loadTableData(true)" title="Обновить"/>

            <v-btn color="green" @click="openEditDialog()">Создать</v-btn>

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
                          v-for="element in columns"
                          :key="element.id"
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
          </v-toolbar>
        </template>

        <template v-slot:item="{ item }">
          <tr>
            <td v-for="column in headers" :key="column.key">
              <v-chip
                v-if="isColorColumn(column, item[column.key])"
                :color="item[column.key]"
                dark
                label
              >
                {{ item[column.key] }}
              </v-chip>
              <span v-else-if="isIconColumn(column, item[column.key])">
                <m-icon :icon="item[column.key]" size="20" class="me-2"/>
              </span>
              <v-icon
                v-else-if="isBooleanColumn(column, item[column.key])"
                :color="item[column.key] ? 'green' : 'grey'"
              >
                {{ item[column.key] ? 'mdi-check-circle' : 'mdi-close-circle' }}
              </v-icon>
              <MyFormField
                v-else-if="column?.element?.type === 'alias'"
                v-model="item[column.key]"
                :field="column"
                :only_value="true"
                :disabled="true"
              />
              <span v-else-if="isLinkColumn(column, item[column.key])">
                <a :href="item[column.key]" target="_blank">{{ item[column.key] }}</a>
              </span>
              <span v-else-if="isDateColumn(column, item[column.key])">
                {{ formatDate(item[column.key]) }}
              </span>
              <span v-else-if="column?.id === '__actions'">
                <v-btn icon="mdi-pencil" @click.stop="openEditDialog(item)" size="small" title="Редактировать"/>
                <v-btn icon="mdi-delete" @click.stop="openDeleteDialog(item)" size="small" title="Удалить"/>
              </span>
              <span v-else>
                {{ item[column.key] }}
              </span>
            </td>
          </tr>
        </template>
      </v-data-table>
    </v-card>

    <!-- Диалог редактирования / создания -->
    <v-dialog v-model="dialogEdit" max-width="600px">
      <v-card>
        <v-card-title class="text-h5">
          {{ formData.id ? 'Редактировать запись' : 'Создать запись' }}
        </v-card-title>
        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="12" v-for="field in structure" :key="field.name">
                <MyFormField
                  v-model="formData[field.name]"
                  :field="field"
                  v-if="!field.readonly"
                />
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-spacer/>
          <v-btn text :disabled="formSaving" @click="dialogEdit = false">Отмена</v-btn>
          <v-btn color="blue-darken-1" variant="text" :loading="formSaving" :disabled="formSaving" @click="saveForm">
            Сохранить
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Диалог подтверждения удаления -->
    <v-dialog v-model="dialogDelete" max-width="500px">
      <v-card>
        <v-card-title class="text-h5">
          Вы уверены, что хотите удалить запись?
        </v-card-title>
        <v-card-actions>
          <v-spacer/>
          <v-btn text @click="dialogDelete = false">Отмена</v-btn>
          <v-btn color="red-darken-1" variant="text" @click="deleteItemConfirm">Удалить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script>
import {mapStores} from 'pinia'
import useTableStore from '@/store/tables'
import {VueDraggableNext} from 'vue-draggable-next'
import Null from 'axios/unsafe/helpers/null'
import MyFormField from '@/components/form_elements/MyFormField.vue'

export default {
  components: {
    draggable: VueDraggableNext,
    MyFormField,
  },
  data() {
    return {
      _columns: Null,
      dialogEdit: false,
      dialogDelete: false,
      formData: {},
      selectedItem: null,
      formSaving: false,
      has_set_password: false,
    }
  },
  computed: {
    pageTitle() {
      return this.$route.meta.title || 'Таблица'
    },
    table() {
      return this.$route.meta.tableModel
    },
    items() {
      return this.tablesStore.tables[this.table]?.items || []
    },
    permissions() {
      return this.tablesStore.tables[this.table]?.permissions || {}
    },
    structure() {
      const struct = this.tablesStore.tables[this.table]?.structure || []
      return struct.filter(item => {
        if (item.name === 'password') {
          this.has_set_password = true
          return false
        }
        return true
      })
    },
    headers() {
      return this.columns?.filter(column => column.show) || []
    },
    columns: {
      get() {
        // if (!this._columns) {
        if (1) {
          this._columns = this.structure.map(item => ({
            id: item.name,
            title: item.name,
            key: item.name,
            align: item.align || 'left',
            sortable: item.sortable ?? true,
            show: true,
            element: item?.element,
          }))
          this._columns.push({
            id: '__actions',
            title: 'Действия',
            key: '__actions',
            align: 'center',
            sortable: false,
            show: true,
          })
        }
        return this._columns
      },
      set(value) {
        alert('Сохраните настройки колонок')
        this._columns = value
      },
    },
    ...mapStores(useTableStore),
  },
  created() {
    this.loadTableData()
  },
  methods: {
    isColorColumn(column, value) {
      return column.key.toLowerCase().includes('color') && typeof value === 'string' && value.startsWith('#')
    },
    isIconColumn(column, value) {
      return column.key.toLowerCase().startsWith('icon') && typeof value === 'string'
    },
    isBooleanColumn(column, value) {
      return typeof value === 'boolean'
    },
    isLinkColumn(column, value) {
      return ['url', 'link'].some(k => column.key.toLowerCase().includes(k)) && typeof value === 'string' && value.startsWith('http')
    },
    isDateColumn(column, value) {
      return ['created_at', 'updated_at'].includes(column.key.toLowerCase()) && value
    },
    formatDate(value) {
      try {
        return new Date(value).toLocaleString()
      } catch (e) {
        return value
      }
    },
    loadTableData(reload = false) {
      if (!this.$route.meta.tableModel) return
      if (reload) {
        this.tablesStore.reloadTableData(this.$route.meta.tableModel)
      } else {
        this.tablesStore.loadTableData(this.$route.meta.tableModel)
      }
    },
    openEditDialog(item = null) {
      this.formData = {}
      this.structure.forEach(field => {
        this.formData[field.name] = item ? item[field.name] : null
      })
      if (item?.id) this.formData.id = item.id
      this.dialogEdit = true
    },
    async saveForm() {
      this.formSaving = true
      try {
        const success = await this.tablesStore.saveItem(this.table, this.formData)
        if (success) {
          this.dialogEdit = false
          this.loadTableData(true)
        }
      } catch (e) {
        console.warn(e)
      } finally {
        this.formSaving = false
        this.loadTableData(true)
      }
    },
    openDeleteDialog(item) {
      this.selectedItem = item
      this.dialogDelete = true
    },
    async deleteItemConfirm() {
      await this.tablesStore.deleteItem(this.table, this.selectedItem.id)
      this.dialogDelete = false
      this.loadTableData(true)
    },
  },
  watch: {
    '$route': {
      handler() {
        this.loadTableData()
      },
      immediate: true,
    },
    tablesStore: {
      handler() {
        this._columns = null
      },
      deep: true,
    },
  },
}
</script>
