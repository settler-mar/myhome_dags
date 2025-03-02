<template>
  <div class="tabs">
    <div class="tab" v-for="(tab, index) in out_list" :key="index"
         @click="$emit('update:model', index)"
         :class="{ active: model === index }">
      {{ tab.title }}

      <template v-if="tab.save && on_save">
        <span v-if="tab.on_save" class="need_save on_save">
          <v-icon size="x-small">mdi-content-save</v-icon>
        </span>
        <span v-else class="need_save" @click="on_save(index)">
        <v-icon size="x-small">mdi-content-save</v-icon>
      </span>
      </template>
      <span class="close_tab" v-if="tab.close && on_close" @click="on_close(index)">
        <v-icon size="x-small">mdi-close</v-icon>
      </span>
    </div>
    <div v-if="add_button" class="tab tab-add" @click="add_button()">+</div>
  </div>
</template>

<script>

export default {
  name: 'Tabs',
  props: {
    model: {
      type: String,
    },
    list: {
      type: Object,
    },
    add_button: { // function to add new tab
      // type: callback,
      default: null
    },
    on_close: { // function to close tab
      // type: callback,
      default: null
    },
    on_save: { // function to save tab
      // type: callback,
      default: null
    }
  },
  // emits:{
  //   add_button: null
  // },
  computed: {
    out_list() {
      if (Array.isArray(this.list)) {
        let out_list = {}
        for (let i = 0; i < this.list.length; i++) {
          if (typeof this.list[i] === 'string') {
            out_list[this.list[i]] = {'title': this.list[i]}
          } else {
            out_list[this.list[i].id || this.list[i].title] = this.list[i]
          }
        }
        return out_list
      }
      /*for (let [key, value] of Object.entries(this.list)) {
        if (typeof value === 'string') {
          // this.list[key] = {'title': value}
        }
      }*/
      return this.list || {}
    }
  }
}

</script>


<style scoped lang="scss">
.tabs {
  display: flex;
  justify-content: center;
  margin: 20px 0;
}

.tab {
  padding: 10px 20px;
  cursor: pointer;
  border: 2px solid #ccc;
  border-radius: 5px;
  margin: 0 5px;
  background-color: #f0f0f0;
  transition: all 0.3s;
  position: relative;
  color: #000;

  &:hover {
    background-color: #e0e0e0;
  }

  &.active {
    background-color: #ccc;
    border: 2px solid #000;
  }
}

.close_tab, .need_save {
  position: absolute;
  right: -5px;
  top: -5px;
  background: #fff;
  padding: 2px;
  border: 2px solid;
  border-radius: 5px;
  font-size: 14px;
  line-height: 12px;
  transition: all 0.3s;
  cursor: pointer;

  &:hover {
    background: #f00;
    color: #fff;
    border-color: #f00;
  }
}

.need_save {
  right: 15px;

  &:hover {
    background: #0f0;
    color: #fff;
    border-color: #0f0;
  }

  &.on_save {
    background: #5b775b;
    color: #fff;
    border-color: #000000;
  }
}
</style>
