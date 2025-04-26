<template>
  <v-container fluid>
    <v-row class="mb-4" align="center">
      <v-col cols="12" sm="6" md="3">
        <v-select
          v-model="viewMode"
          :items="viewModes"
          label="Стартовый уровень"
          dense
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-select
          v-model="locationFilter"
          :items="availableLocations"
          label="Фильтр по локации"
          clearable
          dense
        />
      </v-col>
    </v-row>

    <v-btn v-if="viewMode==='connection'" color="primary" @click="openDialog({})" compact class="btn-add-connection">
      🔌 Add connection
    </v-btn>

    <v-row>
      <template v-if="viewMode === 'connection'">
        <v-col cols="12" md="12" v-for="conn in filteredConnections" :key="conn.id">
          <ConnectionCard :connection="conn" :readonly="false" @edit="editConnect"/>
        </v-col>
      </template>

      <template v-else-if="viewMode === 'device'">
        <v-col cols="12" sm="6" md="4" v-for="dev in filteredDevices" :key="dev.id">
          <DeviceCard :device="dev" :readonly="false"/>
        </v-col>
      </template>

      <template v-else-if="viewMode === 'location'">
        <LocationGroup
          v-for="(group, loc) in groupedByLocation"
          :key="loc"
          :location="loc"
          :devices="group"
          :readonly="false"
        />
      </template>
    </v-row>

    <ConnectionDialog
      v-model="dialog"
      :connection="selectedConnection"
      @save="onSave"
      @cancel="dialog = false"
    />
  </v-container>
</template>

<script setup>
import {ref, computed, onMounted} from 'vue'
import {useTableStore} from '@/store/tables'
import {useConnectionsStore} from '@/store/connectionsStore'
import {usePortsStore} from '@/store/portsStore';

import ConnectionCard from '@/components/devices/ConnectionCard.vue'
import DeviceCard from '@/components/devices/DeviceCard.vue'
import LocationGroup from '@/components/devices/LocationGroup.vue'
import ConnectionDialog from '@/components/devices/ConnectionDialog.vue'


const viewMode = ref('connection')
const locationFilter = ref(null)
const dialog = ref(false)
const selectedConnection = ref(null)

const viewModes = [
  {title: 'Подключения', value: 'connection'},
  {title: 'Устройства', value: 'device'},
  {title: 'Локация', value: 'location'},
]

const store = useTableStore()
const connectionsStore = useConnectionsStore()
const portsStore = usePortsStore()

const connections = computed(() => store.tables.connections?.items || [])
const devices = computed(() => store.tables.devices?.items || [])
const ports = computed(() => store.tables.ports?.items || [])

const getDeviceLocation = (device) => {
  return device.location || ports.value.find(p => p.device_id === device.id)?.location || 'Без локации'
}

const availableLocations = computed(() => {
  const locs = new Set()
  for (const dev of devices.value) {
    const loc = getDeviceLocation(dev)
    if (loc) locs.add(loc)
  }
  return Array.from(locs)
})

const filteredDevices = computed(() => {
  return locationFilter.value
    ? devices.value.filter(d => getDeviceLocation(d) === locationFilter.value)
    : devices.value
})

const filteredConnections = computed(() => {
  if (!locationFilter.value) return attachDevicesToConnections(connections.value)
  const devIds = filteredDevices.value.map(d => d.id)
  return attachDevicesToConnections(connections.value).filter(c =>
    c.devices?.some(d => devIds.includes(d.id))
  )
})

const groupedByLocation = computed(() => {
  const result = {}
  for (const dev of filteredDevices.value) {
    const loc = getDeviceLocation(dev)
    if (!result[loc]) result[loc] = []
    result[loc].push({...dev, ports: ports.value.filter(p => p.device_id === dev.id)})
  }
  return result
})

function attachDevicesToConnections(connections) {
  return connections.map(conn => ({
    ...conn,
    devices: devices.value
      .filter(d => d.connection_id === conn.id)
      .map(d => ({
        ...d,
        ports: ports.value.filter(p => p.device_id === d.id)
      }))
  }))
}

function openDialog(connection = null) {
  selectedConnection.value = connection
  dialog.value = true
}

function onSave() {
  dialog.value = false
  selectedConnection.value = null
  store.reloadTableData('connections')
}

function editConnect(connection) {
  openDialog(connection)
}

onMounted(() => {
  portsStore.loadPorts()
  store.loadTableData('connections')
  store.loadTableData('devices')
  store.loadTableData('ports')
  store.loadTableData('port_metadata')
  store.loadTableData('locations')
  connectionsStore.fetchAvailable()
  connectionsStore.fetchLive()
})

</script>

<style>
.btn-add-connection {
  margin-bottom: 16px;
  margin-top: -40px;
}
</style>
