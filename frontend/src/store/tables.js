import {defineStore} from "pinia";
import useDagsStore from "@/store/dags";
import {secureFetch} from "@/services/fetch";

export const useTableStore = defineStore("tables", {
  state: () => ({
    tables: {},
  }),
  actions: {
    async loadTableData(tableModel) {
      console.log('loadTableData', tableModel)
      if (this.tables[tableModel] === undefined) {
        this.tables[tableModel] = {};
      } else {
        return
      }

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
          const data = await secureFetch(`/api/${tableModel}`)
          const data_data = await data.json();
          this.tables[tableModel].items = data_data;
          console.log('data_data', data_data)
        }
      }
    },
  }
});

export default useTableStore;
