<template>
  <span
    v-if="type === 'font'"
    :class="[`icon-${code}`, `icon-${folder}`, 'inline-icon']"
    :style="`font-size: ${size}px`"
  />
  <img
    v-else-if="type === 'img'"
    :src="`/api/fonts/icons/${folder}/${code}.svg`"
    :alt="code"
    :style="`height: ${size}px; width: ${size}px`"
  />
  <svg
    v-else
    :style="`height: ${size}px; width: ${size}px`"
    v-html="rawSvg"
    class="inline-icon"
  />
</template>

<script setup>
import {onMounted, ref, watchEffect} from 'vue'
import {secureFetch} from "@/services/fetch";
import {useIconStore} from '@/store/iconStore'

const store = useIconStore()

const props = defineProps({
  code: String,
  folder: String,
  size: {
    type: [Number, String],
    default: 20,
  },
  type: {
    type: String,
    default: 'font', // font | svg | img
  },
})

const rawSvg = ref('')

watchEffect(async () => {
  if (props.type === 'svg') {
    try {
      const res = await secureFetch(`/api/fonts/icons/${props.folder}/${props.code}.svg`)
      rawSvg.value = await res.text()
    } catch (e) {
      rawSvg.value = ''
    }
  }
})

onMounted(async () => {
  store.loadConfig()
  if (props.type === 'font') {
    const icon = store.config.find(i => i.name === props.code)
    if (!icon) {
      await store.add_to_notfound(props.code)
    }
  }
})
</script>

<style scoped>
.inline-icon {
  display: inline-block;
  vertical-align: middle;
  line-height: 1;
  text-align: center;
}
</style>
