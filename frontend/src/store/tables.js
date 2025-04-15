import {defineStore} from "pinia";
import useDagsStore from "@/store/dags";
import {secureFetch} from "@/services/fetch";
import useMessageStore from "@/store/messages";

export const useTableStore = defineStore("tables", {
  state: () => ({
    tables: {},
  }),
  actions: {
    clear(tableModel) {
      console.log('clear', tableModel)
      if (this.tables[tableModel] !== undefined) {
        this.tables[tableModel].items = [];
        this.tables[tableModel].structure = [];
        this.tables[tableModel].permissions = {};
        this.tables[tableModel] = undefined;
      }
    },
    async reloadTableData(tableModel) {
      const messageStore = useMessageStore();
      if (this.tables[tableModel] === undefined) {
        await this.loadTableData(tableModel)
        return
      }
      console.log('reloadTableData', tableModel)
      // load this table data only
      this.tables[tableModel].items = [];
      if (this.tables[tableModel].permissions.view) {
        try {
          const data = await secureFetch(`/api/${tableModel}/`)
          const data_data = await data.json();
          this.tables[tableModel].items = data_data;
          messageStore.addMessage({type: 'info', text: "Данные успешно обновлены."});
        } catch (e) {
          console.warn(e)
        }
      }
    },
    async loadTableData(tableModel) {
      const messageStore = useMessageStore();
      console.log('loadTableData', tableModel)
      if (this.tables[tableModel] === undefined) {
        this.tables[tableModel] = {};
      } else {
        return
      }

      try {
        const permissions = await secureFetch(`/api/permissions/${tableModel}/my`)
        const permissions_data = await permissions.json()
        this.tables[tableModel].permissions = permissions_data;
        console.log('permissions_data', permissions_data)

        if (permissions_data.get_structure) {
          const structure = await secureFetch(`/api/structure/${tableModel}`)
          const structure_data = await structure.json();
          this.tables[tableModel].structure = structure_data;
          console.log('structure_data', structure_data)

          for (const field of structure_data) {
            if (field.element !== undefined) {
              if (field.element.type === 'alias') {
                await this.loadTableData(field.element.table)
              }
            }
          }

          if (permissions_data.view) {
            const data = await secureFetch(`/api/${tableModel}/`)
            const data_data = await data.json();
            this.tables[tableModel].items = data_data;
            console.log('data_data', data_data)
          }
        }
      } catch (e) {
        console.warn(e)
        messageStore.addMessage({type: "error", text: "Ошибка при загрузке данных."});
      }
    },

    async saveItem(table, data) {
      console.log('saveItem', table, data)
      const messageStore = useMessageStore();
      const method = data.id ? 'PUT' : 'POST'
      const url = `/api/${table}/${data.id || ''}`
      // only send fields that are in the structure not readonly
      const send_data = {}
      for (const field of this.tables[table].structure) {
        if (field.readonly !== true && data[field.name] !== undefined && data[field.name] !== null) {
          send_data[field.name] = data[field.name]
        }
      }
      try {
        await secureFetch(url, {
          method,
          headers: {'Content-Type': 'application/json'},
          body: send_data,
        })
        await this.loadTableData(table)
        messageStore.addMessage({
          type: "info",
          text: data.id ? "Запись успешно обновлена." : "Запись успешно создана."
        })
        return true
      } catch (e) {
        return false
      }
    },

    async deleteItem(table, id) {
      const messageStore = useMessageStore();
      try {
        await secureFetch(`/api/${table}/${id}`, {
          method: 'DELETE',
        })
        await this.loadTableData(table)
        messageStore.addMessage({type: "info", text: "Запись удалена."})
      } catch (e) {
        console.warn(e)
        messageStore.addMessage({type: "error", text: "Ошибка при удалении записи."})
      }
    },
  }
});

export default useTableStore;
