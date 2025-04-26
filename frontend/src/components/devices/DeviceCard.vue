<template>
  <v-card class="mb-2" elevation="1">
    <v-toolbar density="compact" :elevation="1" border>
      📟 {{ device.name }}
      <v-chip density="comfortable" size="x-small" color="info">id: {{ device.id }}</v-chip>

      <ActionHandler
        :actions="actions"
        :params="{connector_id: device.connector_id, device_id: device.id, ...device, ...(device?.params || {})}"
      >
        <v-btn icon v-if="!readonly" @click="$emit('edit', device)">
          <m-icon size="18" code="mdi-pencil"/>
        </v-btn>
      </ActionHandler>
    </v-toolbar>

    <v-row
      v-if="hasStatusInfo"
      dense
      align="center"
      class="px-2 py-1"
      style="background-color: #f5f5f5; min-height: 32px; font-size: 13px; color: #555;"
    >
      <v-col v-if="device.location_id" cols="auto" class="d-flex align-center">
        <m-icon size="18" code="mdi-map-marker" class="mr-1"/>
        <my-form-field
          v-model="device.location_id"
          :field="device_schema?.location_id"
          :only_value="true"
          density="compact"
        />
      </v-col>

      <v-spacer/>

      <v-col v-for="port in diagnosticPorts" :key="port.id" cols="auto" class="d-flex align-center">
        <v-tooltip location="top">
          <template #activator="{ props }">
            <div v-bind="props" class="d-flex align-center">
              <m-icon size="18" :code="(port_metadata[port.metadata_id] || {}).icon"/>
              <span class="ml-1">{{ getPortValue(port) }} {{ port.unit || '' }}</span>
            </div>
          </template>
          {{ port.label || port.name }}
        </v-tooltip>
      </v-col>

      <v-col v-if="powerSource" cols="auto" class="d-flex align-center">
        <v-tooltip location="top">
          <template #activator="{ props }">
            <div v-bind="props" class="d-flex align-center">
              <m-icon size="18" :code="powerSourceIcon"/>
            </div>
          </template>
          {{ powerSource }}
        </v-tooltip>
      </v-col>

      <v-col cols="auto" class="d-flex align-center">
        <v-tooltip location="top">
          <template #activator="{ props }">
            <div @click="editPortsDialog = true" class="nav_bar_button">
              <m-icon size="18" code="mdi-cog"/>
            </div>
          </template>
          Редатировать порты
        </v-tooltip>
      </v-col>

      <v-col v-if="showOptionsConfig" cols="auto" class="d-flex align-center">
        <v-tooltip location="top">
          <template #activator="{ props }">
            <div @click="editOptionsDialog = true" class="nav_bar_button">
              <m-icon size="18" code="mdi-tune-variant"/>
            </div>
          </template>
          Управление опциями
        </v-tooltip>
      </v-col>
    </v-row>

    <v-card-text>
      <v-row v-if="device.description">
        <v-col cols="12">
          {{ device.description }}
        </v-col>
      </v-row>

      <v-divider v-if="groupedPortsKeys.length > 1" class="my-2"/>

      <div v-for="group in groupedPortsKeys" :key="group">
        <div v-if="group">
          <div class="text-subtitle-2 text-grey-darken-1 mb-2 mt-2">{{ group }}</div>
        </div>

        <v-row>
          <v-col cols="12">
            <div
              :style="groupedPorts[group].length > maxPortsWithoutScroll ? 'max-height:300px; overflow-y:auto;' : ''">
              <v-table density="compact">
                <tbody>
                <tr v-for="port in sortedPorts(groupedPorts[group])" :key="port.id"
                    v-show="!isConfig(port) || showConfigPorts">
                  <td style="width:24px" class="py-1">
                    <m-icon v-if="port.metadata_id && port_metadata[port.metadata_id]?.icon"
                            size="18"
                            :code="port_metadata[port.metadata_id]?.icon"/>
                  </td>
                  <td class="py-1">
                    <v-tooltip location="top">
                      <template #activator="{ props }">
                        <div v-bind="props" class="d-flex align-center">
                          <span>{{ port.label || port.name }}</span>
                        </div>
                      </template>
                      {{ port.description || '' }}
                    </v-tooltip>
                  </td>
                  <td class="py-1 text-right">
                    <span>{{ getPortValue(port) }}</span>
                  </td>
                  <td class="py-1">
                    {{ port.unit || '' }}
                  </td>
                </tr>
                </tbody>
              </v-table>
            </div>
          </v-col>
        </v-row>
      </div>
    </v-card-text>

    <!-- Диалог управления портами -->
    <v-dialog v-model="editPortsDialog" max-width="1000px">
      <v-card>
        <v-card-title>Порты устройства</v-card-title>
        <v-card-text>
          <v-data-table :items="props.device.ports || []" :headers="portsHeaders" density="compact" class="elevation-1">
            <template #item.actions="{ item }">
              <v-btn icon size="small" @click="editPort(item)" title="Редактировать">
                <m-icon size="18" code="mdi-pencil"/>
              </v-btn>
              <v-btn icon size="small" @click="deletePort(item)" title="Удалить">
                <m-icon size="18" code="mdi-delete"/>
              </v-btn>
            </template>
          </v-data-table>
        </v-card-text>
        <v-card-actions>
          <v-spacer/>
          <v-btn color="green" @click="addPort">Добавить порт</v-btn>
          <v-btn text @click="editPortsDialog = false">Закрыть</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Диалог управления options/config -->
    <v-dialog v-model="editOptionsDialog" max-width="600px">
      <v-card>
        <v-tabs v-model="optionsTab" background-color="primary" dark>
          <v-tab v-if="optionsPorts.length" value="options">Options</v-tab>
          <v-tab v-if="configPorts.length" value="config">Config</v-tab>
        </v-tabs>
        <v-tabs-window v-model="optionsTab">
          <v-tabs-window-item value="options" v-if="optionsPorts.length">
            <v-card-text>
              <table>
                <tr v-for="port in optionsPorts" :key="port.id">
                  <td>
                    <v-tooltip location="top">
                      <template #activator="{ props }">
                        <div v-bind="props" class="d-flex align-center">
                          <span>{{ port.label || port.name }}</span>
                        </div>
                      </template>
                      {{ port.description || '' }}
                    </v-tooltip>
                  </td>
                  <td class="py-1 text-right">
                    <span class="ml-1">{{ getPortValue(port) }}</span>
                  </td>
                </tr>
              </table>
            </v-card-text>
          </v-tabs-window-item>
          <v-tabs-window-item value="config" v-if="configPorts.length">
            <v-card-text>
              <table>
                <tr v-for="port in configPorts" :key="port.id">
                  <td>
                    <v-tooltip location="top">
                      <template #activator="{ props }">
                        <div v-bind="props" class="d-flex align-center">
                          <span>{{ port.label || port.name }}</span>
                        </div>
                      </template>
                      {{ port.description || '' }}
                    </v-tooltip>
                  </td>
                  <td class="py-1 text-right">
                    <span class="ml-1">{{ getPortValue(port) }}</span>
                  </td>
                </tr>
              </table>
            </v-card-text>
          </v-tabs-window-item>
        </v-tabs-window>


        <v-card-actions>
          <v-spacer></v-spacer>

          <v-btn
            text="Close"
            @click="editOptionsDialog = false"
          ></v-btn>
        </v-card-actions>
      </v-card>

    </v-dialog>

  </v-card>
</template>

<script setup>
import {ref, computed} from 'vue'
import ActionHandler from '@/components/devices/ActionHandler.vue'
import {useConnectionsStore} from '@/store/connectionsStore'
import {useTableStore} from '@/store/tables'
import MyFormField from '@/components/form_elements/MyFormField.vue'
import {usePortsStore} from '@/store/portsStore';

const props = defineProps({
  device: Object,
  readonly: {
    type: Boolean,
    default: false
  },
})

const emit = defineEmits(['edit'])

const connectionsStore = useConnectionsStore()
const tableStore = useTableStore()
const portsStore = usePortsStore()

const port_metadata = computed(() => {
  const metadata = {}
  for (const port of tableStore.tables?.port_metadata?.items || []) {
    metadata[port.id] = port
  }
  return metadata
})

const ports = computed(() => (props.device.ports || []).filter(p => p && p.mode === 'exposes'))
const groupedPorts = computed(() => {
  const groups = {}
  for (const port of ports.value) {
    const group = port.groups_name || ''
    if (!groups[group]) groups[group] = []
    groups[group].push(port)
  }
  return groups
})
const groupedPortsKeys = computed(() => Object.keys(groupedPorts.value))

const maxPortsWithoutScroll = 10
const showConfigPorts = ref(false)
const editPortsDialog = ref(false)
const editOptionsDialog = ref(false)
const optionsTab = ref(0)

const portsHeaders = [
  {title: 'ID', key: 'id'},
  {title: 'Код', key: 'code'},
  {title: 'Имя', key: 'name'},
  {title: 'Метка', key: 'label'},
  {title: 'Тип', key: 'type'},
  {title: 'Ед.', key: 'unit'},
  {title: 'Описание', key: 'description'},
  {title: '', key: 'actions', sortable: false},
]

const sortedPorts = (portsList) => {
  const nonConfig = portsList.filter(p => !isConfig(p))
  const config = portsList.filter(p => isConfig(p))
  return [...nonConfig, ...config]
}

const isConfig = (port) => port.mode === 'config'
const isDiagnostic = (port) => port.mode === 'diagnostic'
const isOptions = (port) => port.mode === 'options'

const diagnosticPorts = computed(() => (props.device.ports || []).filter(p => isDiagnostic(p)))
const optionsPorts = computed(() => (props.device.ports || []).filter(p => isOptions(p)))
const configPorts = computed(() => (props.device.ports || []).filter(p => isConfig(p)))

const showOptionsConfig = computed(() => optionsPorts.value.length || configPorts.value.length)

const connection = computed(() => tableStore.tables.connections?.items.find(c => c.id === props.device?.connection_id) || {})
const connectionDef = computed(() => connectionsStore.available.find(c => c.code === connection?.value?.type))
const actions = computed(() => connectionDef.value?.actions?.filter(a => a.scope === 'device') || [])

const powerSource = computed(() => props.device?.params?.power_source ?? null)
const powerSourceIcon = computed(() => {
  if (!powerSource.value) return 'mdi-power-plug'
  return powerSource.value.toLowerCase().includes('battery') ? 'mdi-battery' : 'mdi-power-plug'
})

const hasStatusInfo = computed(() => {
  return diagnosticPorts.value.length > 0 || powerSource.value
})

const device_schema = computed(() => {
  let structure = tableStore.tables.devices?.structure || []
  let schema = {}
  for (const field of structure) {
    schema[field.name] = field
  }
  return schema
})

function getPortValue(port) {
  const live_port = portsStore.ports[port.id];
  if (live_port && live_port.value !== undefined && live_port.value !== null) {
    return live_port.value;
  }
  return port.value ?? '-';
}

function addPort() {
  console.log('Добавить порт');
}

function editPort(port) {
  console.log('Редактировать порт', port);
}

function deletePort(port) {
  console.log('Удалить порт', port);
}
</script>


<style scoped>
.nav_bar_button {
  cursor: pointer;
  color: #2196F3;
  transition: color 0.2s;
}

.nav_bar_button:hover {
  color: #1a7b9c;
}
</style>
