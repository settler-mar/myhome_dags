<template>
  <component
    :is="tag"
    v-if="resolvedType === 'font'"
    :class="iconClass"
    :style="[fontStyle, inlineStyle]"
    v-bind="attrs"
    :aria-hidden="ariaHidden"
    :aria-label="ariaLabel"
    role="img"
  />

  <img
    v-else-if="resolvedType === 'img'"
    :src="`/api/fonts/icons/${resolvedFolder}/${resolvedCode}.svg`"
    :alt="ariaLabel || resolvedCode"
    :class="['inline-icon', { 'm-icon--disabled': disabled }]"
    :style="[dimensionStyle, inlineStyle]"
    v-bind="attrs"
    :aria-hidden="ariaHidden"
    role="img"
  />

  <svg
    v-else
    v-html="rawSvg"
    :class="['inline-icon', { 'm-icon--disabled': disabled }, ...iconClass]"
    :style="[dimensionStyle, inlineStyle]"
    v-bind="attrs"
    :aria-hidden="ariaHidden"
    role="img"
  />
</template>

<script setup>
import {ref, watchEffect, computed, onMounted} from 'vue'
import {useIconStore} from '@/store/iconStore'
import {secureFetch} from '@/services/fetch'
import {useAttrs} from 'vue'

const props = defineProps({
  icon: String,
  code: String,
  folder: String,
  size: [Number, String],
  type: String,
  color: String,
  opacity: [Number, String],
  disabled: Boolean,
  class: [String, Array, Object],
  tag: {type: String, default: 'i'},
  start: Boolean,
  end: Boolean,
  ariaLabel: String,
  ariaHidden: {type: [Boolean, String], default: true},

  xSmall: Boolean,
  small: Boolean,
  medium: Boolean,
  large: Boolean,
  xLarge: Boolean,
})

const attrs = useAttrs()
const store = useIconStore()

// Авторазбор icon="folder/name" на folder + name
const iconParts = computed(() => {
  const input = props.code || props.icon || ''
  const [folder, ...rest] = input.replace(/^mdi-/, '').split('/')
  const name = rest.length ? rest.join('/') : folder
  return {
    folder: rest.length ? folder : props.folder || null,
    name,
  }
})

const resolvedCode = computed(() => iconParts.value.name)
const resolvedFolder = computed(() => props.folder || iconParts.value.folder)

const resolvedType = computed(() => {
  if (props.type) return props.type
  if (props.icon?.startsWith('img:')) return 'img'
  if (props.icon?.startsWith('svg:')) return 'svg'
  return 'font'
})

const vuetifySizeMap = {
  'x-small': '1em',
  'small': '1.25em',
  'default': '1.5em',
  'medium': '1.6em',
  'large': '1.75em',
  'x-large': '2em',
}

const extractSizeClass = () => {
  const classes = Array.isArray(props.class)
    ? props.class
    : typeof props.class === 'string'
      ? props.class.split(' ')
      : Object.keys(props.class || {})

  const sizeClass = classes?.find(c => c.startsWith('v-icon--size-'))
  const key = sizeClass?.replace('v-icon--size-', '')
  return vuetifySizeMap[key] || undefined
}


const resolveSize = () => {
  if (props.xSmall) return vuetifySizeMap['x-small']
  if (props.small) return vuetifySizeMap['small']
  if (props.medium) return vuetifySizeMap['medium']
  if (props.large) return vuetifySizeMap['large']
  if (props.xLarge) return vuetifySizeMap['x-large']

  if (typeof props.size === 'number' || (typeof props.size === 'string' && /^\d+$/.test(props.size))) {
    return `${props.size}px`
  }
  if (vuetifySizeMap[props.size]) return vuetifySizeMap[props.size]
  return extractSizeClass() || vuetifySizeMap['default']
}

const resolvedSize = computed(() => resolveSize())
const fontStyle = computed(() => `font-size: ${resolvedSize.value}`)
const dimensionStyle = computed(() => ({
  width: resolvedSize.value,
  height: resolvedSize.value,
}))
const inlineStyle = computed(() => ({
  opacity: props.disabled ? 0.4 : props.opacity ?? undefined,
  cursor: props.disabled ? 'not-allowed' : undefined,
}))
const iconClass = computed(() => [
  props.class,
  'inline-icon',
  `icon-${resolvedCode.value}`,
  resolvedFolder.value && `icon-${resolvedFolder.value}`,
  props.color && `text-${props.color}`,
  {'me-2': props.start, 'ms-2': props.end, 'm-icon--disabled': props.disabled},
])

const rawSvg = ref('')
watchEffect(async () => {
  if (resolvedType.value === 'svg') {
    try {
      const res = await secureFetch(`/api/fonts/icons/${resolvedFolder.value}/${resolvedCode.value}.svg`)
      rawSvg.value = await res.text()
    } catch {
      rawSvg.value = ''
    }
  }
})

onMounted(async () => {
  if (resolvedType.value === 'font') {
    await store.loadConfig()
    const exists = store.config.find(i => i.name === resolvedCode.value)
    if (!exists) {
      if (resolvedFolder.value) {
        await store.add_to_notfound(`${resolvedFolder.value}/${resolvedCode.value}`)
      } else {
        await store.add_to_notfound(`${resolvedCode.value}`)
      }
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
  height: 1em;
  width: 1em;
}

.m-icon--disabled {
  pointer-events: none;
}
</style>
