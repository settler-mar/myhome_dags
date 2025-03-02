<template>
  <v-card class="pa-5">
    <v-card-title>{{ title }}</v-card-title>
    <v-list dense>
      <v-list-item
        v-for="(item, index) in value"
        :key="index"
        class="editable-item"
        @click="editItem(index)"
      >
        <template v-if="editingIndex === index">
          <v-text-field
            v-model="value[index]"
            autofocus
            dense
            variant="underlined"
            @blur="editingIndex = null"
            @keyup.enter="editingIndex = null"
          ></v-text-field>
        </template>

        <template v-else>
          <v-list-item-title>
            {{ item || '---' }}
          </v-list-item-title>
          <v-btn
            icon
            color="error"
            class="delete-btn"
            @click.stop="removeItem(index)"
          >
            <v-icon>mdi-delete</v-icon>
          </v-btn>
        </template>
      </v-list-item>
    </v-list>

    <v-btn color="primary" block @click="addItem">
      {{ addButtonLabel }}
    </v-btn>
  </v-card>
</template>

<script>
import {vShow} from "vue";

export default {
  name: 'ListInput',
  props: {
    modelValue: {
      type: Array,
      default: () => []
    },
    title: {
      type: String,
      default: 'Редактирование массива'
    },
    addButtonLabel: {
      type: String,
      default: 'Добавить элемент'
    }
  },
  data() {
    return {
      editingIndex: null
    };
  },
  computed: {
    vShow() {
      return vShow
    },
    value: {
      get() {
        return this.modelValue || [];
      },
      set(newValue) {
        this.$emit('update:modelValue', newValue);
      }
    }
  },
  methods: {
    addItem() {
      this.value.push('');
      this.editingIndex = this.value.length - 1;
      this.$emit('update:modelValue', this.value);
    },
    removeItem(index) {
      this.value.splice(index, 1);
    },
    editItem(index) {
      this.editingIndex = index;
    }
  }
};
</script>

<style scoped>
.editable-item {
  cursor: pointer;
  transition: background-color 0.2s;
}

.editable-item:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.delete-btn {
  opacity: 0;
  transition: opacity 0.2s;
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
}

.editable-item:hover .delete-btn {
  opacity: 1;
}
</style>
