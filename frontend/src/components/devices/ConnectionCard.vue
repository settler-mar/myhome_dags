<template>
  <v-card class="mb-4" elevation="2">
    <v-toolbar density="compact" :elevation="2" border>
      <template v-slot:prepend>
        <span class="mr-2">{{ connectionIcon }}</span>
      </template>

      {{ connection.name }}

      <v-chip density="comfortable" size="x-small">{{ connection_type }}</v-chip>
      <v-chip density="comfortable" size="x-small" color="secondary">id: {{ connection.id }}</v-chip>


      <ActionHandler
        :actions="actions"
        :params="{
          'connection_id': connection.id,
        }"
      >
        <v-btn icon v-if="permissions.add_device" @click="openDialog({})">
          <v-icon>mdi-plus</v-icon>
        </v-btn>
        <v-btn icon v-if="permissions.edit_connection" @click="$emit('edit', connection)">
          <v-icon>mdi-pencil</v-icon>
        </v-btn>
        <DelButton
          v-if="permissions.delete_connection"
          :id="connection.id"
          table="connections"
          @deleted="$emit('deleted')"
        />
      </ActionHandler>
    </v-toolbar>

    <v-card-text>
      <v-row>
        <v-col
          cols="12"
          sm="6"
          md="4"
          v-for="device in connection.devices || []"
          :key="device.id"
        >
          <DeviceCard :device="device" :readonly="readonly" @edit="editDevice"/>
        </v-col>
      </v-row>
    </v-card-text>

    <UniversalDialog
      v-model:show="addDeviceDialog"
      :table="'devices'"
      :parent-id="connection.id"
      :item="connectionData"
      :custom_params="devicesParams"
      @save="onDeviceAdded"
      :permissions="permissions"
    />
  </v-card>
</template>

<script setup>
import {ref, computed} from 'vue'
import DeviceCard from '@/components/devices/DeviceCard.vue'
import DelButton from '@/components/UI/DelButton.vue'
import UniversalDialog from '@/components/devices/UniversalDialog.vue'
import ActionHandler from '@/components/devices/ActionHandler.vue'
import {useConnectionsStore} from '@/store/connectionsStore'

const props = defineProps({
  connection: Object,
  readonly: Boolean
})

const emit = defineEmits(['edit', 'deleted', 'refresh', 'action'])

const addDeviceDialog = ref(false)
const connectionData = ref({})

const connectionsStore = useConnectionsStore()

const connectionDef = computed(() => {
  return connectionsStore.available.find(c => c.code === props.connection?.type)
})

const connectionIcon = computed(() => {
  return connectionDef.value?.icon || '🔌'
})

const connection_type = computed(() => {
  return connectionDef.value?.name || 'Неизвестный тип'
})

const devicesParams = computed(() => {
  const list = connectionDef.value?.devices_params
  return Array.isArray(list) ? list[0] || {} : list || {}
})

const actions = computed(() => {
  return connectionDef.value?.actions?.filter(a => a.scope === 'connection') || []
})


const permissions = computed(() => {
  const rules = connectionDef.value?.rules || {}
  return {
    add_device: rules.allow_device_add !== false,
    edit_device: rules.allow_device_edit !== false,
    delete_device: rules.allow_device_delete !== false,
    edit_connection: true,
    delete_connection: true
  }
})

function onDeviceAdded() {
  addDeviceDialog.value = false
  emit('refresh')
}


function openDialog(device) {
  addDeviceDialog.value = true
  // convert device to a new object
  // {'id': null, 'name': '', 'params': {'a':12}} => {'id': null, 'name': '', 'params.a': 12, 'connection_id': connection.id}
  const data = {
    ...device,
    connection_id: props.connection.id,
  }

  connectionData.value = data
}

function editDevice(device) {
  openDialog(device)
}

function handleAction(action) {
  const scopeData = {connection_id: props.connection.id}
  emit('action', {action, scopeData})
}
</script>
