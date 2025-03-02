<template>
  <div class="editor__wrap">
    <div>
      <div class="tree_ctrl">
        <my-button @click="addMenu(treeData)" class="btn-sm">Add to menu</my-button>
        <my-button @click="reload" class="btn-sm">Reload</my-button>
        <my-button @click="save" class="btn-sm">Save</my-button>
      </div>
      <Tree :value="treeData" v-slot="{node, index, path, tree}" triggerClass="drag-trigger"
            @change="onChange" :eachDroppable="eachDroppable">
        <div class="node-content">
          <button class="mrs drag-trigger">
            <my-i name="updown-circle" title="move"/>
          </button>

          <span class="node-title" @click="edit(node)">
            <my-i :name="node.icon" v-if="node.icon" class="node-icon"/>
            {{ node.title }}
          </span>

          <button @click="addMenu(node)" v-if="node.type=='menu'">
            <my-i name="folder-circled" title="Add menu"/>
          </button>
          <button @click="addPage(node)" v-if="node.type=='menu'">
            <my-i name="doc-circled" title="Add page"/>
          </button>
          <button @click="deleteItem(treeData,path)">
            <my-i name="trash-circled" title="delate"/>
          </button>
        </div>
      </Tree>
    </div>

    <div v-if="onEdit">
      <table>
        <tr>
          <td>Title</td>
          <td>
            <my-input type="text" v-model="onEdit.title"/>
          </td>
          <td></td>
        </tr>
        <tr>
          <td>Href</td>
          <td>
            <my-input type="text" v-model="onEdit.href"/>
          </td>
        </tr>
        <tr v-if="onEdit.type!='menu'">
          <td>template</td>
          <td>
            <my-input type="text" v-model="onEdit.template"/>
          </td>
        </tr>
        <tr>
          <td>Icon</td>
          <td>
            <my-icon-select v-model="onEdit.icon"/>
          </td>
        </tr>
        <tr v-if="onEdit.type!='menu'">
          <td>Тип</td>
          <td>
            <my-select v-model="onEdit.type" :params="type_list"/>
          </td>
        </tr>
        <tr v-if="onEdit.type=='graph'">
          <td>yAxis</td>
          <td>
            <my-input v-model="onEdit.yAxis"/>
          </td>
        </tr>
      </table>

    </div>
    <div v-if="onEdit && onEdit.type!='menu'">
      <my-button @click="addItem(onEdit)" class="btn-sm">Add</my-button>
      <Tree v-if="onEdit.items" :value="onEdit.items" v-slot="{node, index, path, tree}" triggerClass="drag-trigger"
            @change="onChange" :eachDroppable="eachDroppablePage">
        <button class="mrs drag-trigger">
          <my-i name="updown-circle" title="move"/>
        </button>
        <button @click="deleteItem(onEdit.items,path)">
          <my-i name="trash-circled" title="delate"/>
        </button>
        <my-address type="text" v-model="node.address" :updPath="updPath"/>
        <my-input v-model="node.title" title="Название"/>
      </Tree>
    </div>

  </div>
</template>

<script>
import MyInput from "@/components/UI/MyInput";

var $root = null
import {
  Tree, // Base tree
  Fold, Check, Draggable, // plugins
  foldAll, unfoldAll, cloneTreeData, walkTreeData, getPureTreeData, // utils
} from 'he-tree-vue'
import 'he-tree-vue/dist/he-tree-vue.css' // base style

import {mapState, mapGetters, mapActions, mapMutations} from 'vuex'
import Api from '@/services/Api'
import Device from "@/components/Device";

export default {
  components: {
    MyInput,
    Tree: Tree.mixPlugins([Draggable, Fold])
  },
  data() {
    return {
      selected: null,
      onEdit: false,
      treeData: [],
      type_list: {'text': 'Тектовый', 'graph': 'Графики'},
    }
  },
  computed: {
    ...mapState({
      db: state => state.db,
    }),
  },
  methods: {
    addPage: node => {
      if (!('children' in node)) {
        node['children'] = []
      }
      let id = Math.floor(Math.random() * 10000)
      node['children'].push({
        title: "New page " + id,
        href: "page_" + id,
        template: "{{position}} {{type}} {{name}}",
      })
    },
    addMenu: node => {
      if (node instanceof Array) {
        node.push({title: "New menu", type: 'menu'})
        return
      }
      if (!('children' in node)) {
        node['children'] = []
      }
      node['children'].push({title: "New menu", type: 'menu'})
    },
    addItem: node => {
      if (!('items' in node)) {
        node['items'] = []
      }
      node['items'].push({})
    },
    eachDroppable: (currentPath, tree, store) => {
      if (!currentPath.length) return true
      return tree.getNodeByPath(currentPath).type && tree.getNodeByPath(currentPath).type == 'menu'
    },
    eachDroppablePage: (currentPath, tree, store) => {
      return !currentPath.length
    },
    edit: el => {
      if ($root.onEdit) $root.onEdit._edit = false
      $root.onEdit = el
      $root.onEdit._edit = true
    },
    onChange: el => {
      console.log(JSON.stringify(el.targetTree.treeData))
    },
    setIcon: value => {
      $root.onEdit.icon = value
    },
    deleteItem: (treeData, path) => {
      console.log('deleteItem', treeData, path)
      let list = treeData instanceof Array ? treeData : treeData.children
      if (path.length == 1) {
        list.splice(path[0], 1);
        return
      }
      $root.deleteItem(list[path.shift()], path)
    },
    updPath: (path) => {
      console.log(path)
    },
    addTag(newTag) {
      const tag = {
        name: newTag,
        code: newTag.substring(0, 2) + Math.floor((Math.random() * 10000000))
      }
      this.options.push(tag)
      this.value.push(tag)
    },
    save() {
      Api().post('/config/menu/save', {'menu': this.treeData})
    },
    reload() {
      Api().get('/config/menu/')
        .then(function (response) {
          $root.$store.commit('setDB', {model: 'menu', data: response.data})
          $root.treeData = JSON.parse(JSON.stringify($root.db.menu))
          $root.onEdit = $root.treeData[0].children[0]
        })
    },
  },
  mounted() {
    this.$store.commit('setTitle', 'Меню')
    this.$store.commit('setPage', {'width': 'sm'})
    this.$store.commit('setParent', {'href': '/config/base', 'title': 'Базовые'})
    $root = this
    this.treeData = JSON.parse(JSON.stringify(this.db.menu))
    this.onEdit = this.treeData[0].children[0]
  }
}
</script>

<style scoped>
.tree_ctrl {
  display: flex;
  justify-content: space-between;
}

.editor__wrap {
  display: flex;
}

.he-tree {
  min-width: 300px;
}

.editor__wrap > div {
  margin-left: 20px;
}

.editor__wrap > div:first-child {
  margin-left: 0px;
}

.node-content {
  display: flex;
}

.node-title {
  flex-grow: 2;
  font-size: 14px;
}

.node-icon {
  padding: 0 5px;
  font-size: 20px;
}

.tree-node button {
  opacity: 0;
  cursor: pointer;
}

.tree-node:hover button {
  opacity: .8;
}

.tree-node button:hover {
  opacity: 1;
}

button.drag-trigger {
  cursor: move;
}
</style>
