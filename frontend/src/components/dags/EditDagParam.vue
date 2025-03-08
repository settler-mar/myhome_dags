<template>
  <div>
    <template v-for="param in params">
      <v-text-field
        v-if="['int','float'].indexOf(param.type) !== -1"
        v-model="param.value"
        :label="param.description||param.name"
        type="number"
        :min="param.min"
        :max="param.max"
        :step="param.step"
        :unit="param.unit"
      />
      <v-checkbox
        v-else-if="param.type === 'bool'"
        :label="param.description||param.name"
        v-model="param.value"
      />
      <v-select
        v-else-if="param.type === 'select'"
        v-model="param.value"
        :label="param.description||param.name"
        :items="param.items"
      />
      <ListInput
        v-else-if="param.type === 'list'"
        v-model="param.value"
        :title="param.description||param.name"
      />
      <v-text-field
        v-else
        v-model="param.value"
        :label="param.description||param.name"
        :type="param.type"
      />
    </template>
  </div>
</template>

<script>
import ListInput from "@/components/form_elements/ListInput.vue";

export default {
  name: 'EditDagParam',
  props: {
    params: Array
  },
  components: {
    ListInput
  },
  data() {
    return {}
  },
  methods: {}
}
</script>


<style scoped lang="scss">

</style>
