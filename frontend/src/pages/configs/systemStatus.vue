<template>
  <div class="p-6">
    <div class="flex flex-wrap justify-between items-center gap-4 mb-4">
      <h1 class="text-2xl font-bold">Состояние системы</h1>
      <v-row dense align="center" class="gap-4">
        <v-select
          v-model="refreshInterval"
          :items="intervalOptions"
          item-title="label"
          item-value="value"
          label="Обновлять CPU/Память"
          class="w-40"
          dense
          clearable
        />
        <v-btn :disabled="cooldown" @click="loadStatus(true)" color="primary" text>Обновить всё</v-btn>
        <v-btn :disabled="cooldown" @click="loadStatus(false)" color="primary" text>Обновить графики</v-btn>
      </v-row>
    </div>

    <div v-if="status.loading && !preserveUI">Загрузка...</div>
    <div v-else-if="status.error" class="text-red-500">{{ status.error }}</div>
    <div v-else>
      <v-expansion-panels multiple>
        <v-expansion-panel>
          <v-expansion-panel-title>
            Общая информация
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-row class="info_panel" dense>
              <v-col cols="12" sm="6" md="3">
                <StatusCard title="Хост" icon="mdi-server" class="docker-card">
                  {{ status.system.hostname }}
                </StatusCard>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <StatusCard title="Платформа" icon="mdi-laptop" class="docker-card">
                  {{ status.system.platform }}
                </StatusCard>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <StatusCard title="ОС" icon="mdi-desktop-classic" class="docker-card">
                  {{ status.system.os.system }} {{ status.system.os.release }}
                </StatusCard>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <StatusCard title="Архитектура" icon="mdi-cpu-64-bit" class="docker-card">
                  {{ status.system.os.architecture }}
                </StatusCard>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <StatusCard title="Аптайм" icon="mdi-timer-sand" class="docker-card">
                  {{ formatUptime(status.system.uptime_minutes) }}
                </StatusCard>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <StatusCard title="Загрузка системы" icon="mdi-calendar-clock" class="docker-card">
                  {{ formatDate(status.system.boot_time) }}
                </StatusCard>
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel>
          <v-expansion-panel-title>
            Активные пользователи ({{ status.system.users?.length || 0 }})
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-data-table
              :items="status.system.users"
              :headers="userHeaders"
              class="elevation-1"
              density="compact"
              fixed-header
              height="300"
              items-per-page="-1"
            >
              <template #item.started="{ item }">
                {{ formatDate(item.started * 1000) }}
              </template>
            </v-data-table>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel>
          <v-expansion-panel-title>
            Активные процессы ({{ status.system.processes?.length || 0 }})
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-data-table
              :items="status.system.processes"
              :headers="processHeaders"
              class="elevation-1"
              density="compact"
              fixed-header
              height="400"
              items-per-page="25"
            >
              <template #item.create_time="{ item }">
                {{ formatDate(item.create_time * 1000) }}
              </template>
              <template #item.memory_percent="{ item }">
                {{ item.memory_percent?.toFixed(2) }}%
              </template>
              <template #item.cpu_percent="{ item }">
                {{ item.cpu_percent?.toFixed(2) }}%
              </template>
              <template #item.memory_info.rss="{ item }">
                {{ formatBytes(status.system.memory.total * item.memory_percent / 100) }}
              </template>
            </v-data-table>
          </v-expansion-panel-text>
        </v-expansion-panel>


        <v-expansion-panel>
          <v-expansion-panel-title>
            CPU ({{ status.system.cpu.per_core_usage_percent.length }} ядер, средняя нагрузка: {{
              (
                status.system.cpu.per_core_usage_percent.reduce((a, b) => a + b, 0) /
                status.system.cpu.per_core_usage_percent.length
              ).toFixed(1)
            }}%)
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <StatusCard title="Ядер (физ/лог)" icon="mdi-chip">
              {{ status.system.cpu.physical_cores }}/{{ status.system.cpu.logical_cores }}
            </StatusCard>

            <StatusCard title="Нагрузка (1, 5, 15 мин)" icon="mdi-speedometer">
              {{ status.system.cpu.load_avg_1_5_15.join(', ') }}
            </StatusCard>

            <StatusCard title="Текущая загрузка по ядрам" icon="mdi-speedometer-medium">
              {{ status.system.cpu.per_core_usage_percent.join(', ') }}
            </StatusCard>

            <StatusCard title="Частота CPU (МГц)" icon="mdi-av-timer">
              {{ status.system.cpu.frequency_mhz.current.toFixed(0) }} МГц
              (мин: {{ status.system.cpu.frequency_mhz.min.toFixed(0) }},
              макс: {{ status.system.cpu.frequency_mhz.max.toFixed(0) }})
            </StatusCard>

            <StatusCard title="График нагрузки по ядрам" icon="mdi-chart-bar">
              <LineChart
                :data="cpuHistory"
                :label="cpuLabels"
                :xLabels="timestampLabels"
                type="line"
                :axisSwap="true"
              />
            </StatusCard>
          </v-expansion-panel-text>
        </v-expansion-panel>


        <v-expansion-panel>
          <v-expansion-panel-title>
            Память ({{ formatBytes(status.system.memory.used) }} / {{ formatBytes(status.system.memory.total) }} —
            {{ status.system.memory.percent.toFixed(1) }}%)
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <StatusCard title="Всего памяти" icon="mdi-memory">
              {{ formatBytes(status.system.memory.total) }}
            </StatusCard>
            <StatusCard title="Использовано памяти" icon="mdi-memory">
              {{ formatBytes(status.system.memory.used) }}
            </StatusCard>
            <StatusCard title="Свободно памяти" icon="mdi-memory">
              {{ formatBytes(status.system.memory.available) }}
            </StatusCard>
            <StatusCard title="Процент использования" icon="mdi-percent">
              {{ status.system.memory.percent.toFixed(1) }}%
            </StatusCard>
            <StatusCard title="График использования памяти" icon="mdi-chart-bar">
              <LineChart
                :data="memoryHistory"
                label="Memory %"
                :xLabels="timestampLabels"
                type="line"
              />
            </StatusCard>
          </v-expansion-panel-text>
        </v-expansion-panel>


        <v-expansion-panel>
          <v-expansion-panel-title>
            Диски ({{ status.system.disks.physical?.length || 0 }} устройств)
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-row dense>
              <v-col
                v-for="disk in status.system.disks.physical"
                :key="disk.name"
                cols="12"
              >
                <v-card class="pa-3 docker-card mb-4" elevation="1">
                  <div class="font-bold text-base mb-2">
                    <v-icon icon="mdi-harddisk" class="mr-1" size="18"/>
                    {{ disk.name }} — {{ disk.model }}
                  </div>
                  <div class="text-sm mb-3">
                    <div><strong>Серийный номер:</strong> {{ disk.serial || '—' }}</div>
                    <div><strong>Размер:</strong> {{ formatBytes(disk.size) }}</div>
                    <div><strong>Тип:</strong> {{ disk.rotational ? 'HDD' : 'SSD' }}</div>
                  </div>

                  <v-progress-linear
                    :model-value="100"
                    height="30"
                    color="grey lighten-3"
                    rounded
                  >
                    <template #default>
                      <div class="d-flex h-full disk_wrap">
                        <div
                          v-for="part in disk.partitions"
                          :key="part.name"
                          :style="{
                    width: (part.size / disk.size * 100).toFixed(2) + '%',
                    backgroundColor: part.fstype === 'vfat' ? '#ffcc80' : part.fstype === 'ntfs' ? '#ce93d8' : part.fstype === 'ext4' ? '#80cbc4' : '#90caf9',
                    borderRight: '1px solid white'
                  }"
                          class="d-flex align-center justify-center px-1 text-truncate partition_wrap"
                          title="{{ part.name }} ({{ formatBytes(part.size) }})"
                        >
                          <div class="partition_percent"
                               :style="{ width: (part.fsused / part.size * 100).toFixed(2) + '%' }"/>

                          <div class="text-xxs text-white partition_label">
                            {{ part.label || part.name }}
                          </div>
                        </div>
                      </div>
                    </template>
                  </v-progress-linear>

                  <v-table class="mt-2">
                    <thead>
                    <tr>
                      <th>Раздел</th>
                      <th>Метка</th>
                      <th>ФС</th>
                      <th>Монтирование</th>
                      <th>Размер</th>
                      <th>Использовано</th>
                      <th>Использовано (%)</th>
                      <th>Свободно</th>
                      <th style="width: 50vw;"></th>
                    </tr>
                    </thead>
                    <tbody>
                    <tr v-for="part in disk.partitions" :key="part.name">
                      <td>{{ part.name }}</td>
                      <td>{{ part.label || '—' }}</td>
                      <td>{{ part.fstype || '—' }}</td>
                      <td>{{ part.mountpoint || '—' }}</td>
                      <td>{{ formatBytes(part.size) }}</td>
                      <td>{{ part.fsused ? formatBytes(part.fsused) : '—' }}</td>
                      <td>{{ part.fsused && part.size ? (part.fsused / part.size * 100).toFixed(1) : '—' }}%</td>
                      <td>{{ part.fsused && part.size ? formatBytes(part.size - part.fsused) : '—' }}</td>
                      <td>
                        <v-progress-linear
                          :model-value="part.fsused && part.size ? (part.fsused / part.size * 100).toFixed(1) : 0"
                          height="10"
                          color="blue"
                          rounded
                        />
                      </td>
                    </tr>
                    </tbody>
                  </v-table>
                </v-card>
              </v-col>
            </v-row>

            <StatusCard title="IO статистика" icon="mdi-swap-horizontal">
              <v-row dense>
                <v-col cols="12" sm="6" md="4">
                  <div class="text-sm"><strong>Чтений:</strong> {{ status.system.disks.io.read_count }}</div>
                  <div class="text-sm"><strong>Записей:</strong> {{ status.system.disks.io.write_count }}</div>
                </v-col>
                <v-col cols="12" sm="6" md="4">
                  <div class="text-sm"><strong>Чтение:</strong> {{ formatBytes(status.system.disks.io.read_bytes) }}
                  </div>
                  <div class="text-sm"><strong>Запись:</strong> {{ formatBytes(status.system.disks.io.write_bytes) }}
                  </div>
                </v-col>
                <v-col cols="12" sm="6" md="4">
                  <div class="text-sm"><strong>Слияния чтения:</strong> {{ status.system.disks.io.read_merged_count }}
                  </div>
                  <div class="text-sm"><strong>Слияния записи:</strong> {{ status.system.disks.io.write_merged_count }}
                  </div>
                </v-col>
                <v-col cols="12" sm="6" md="4">
                  <div class="text-sm"><strong>Время чтения:</strong> {{ status.system.disks.io.read_time }} мс</div>
                  <div class="text-sm"><strong>Время записи:</strong> {{ status.system.disks.io.write_time }} мс</div>
                </v-col>
                <v-col cols="12" sm="6" md="4">
                  <div class="text-sm"><strong>Время активности:</strong> {{ status.system.disks.io.busy_time }} мс
                  </div>
                </v-col>
              </v-row>
            </StatusCard>
          </v-expansion-panel-text>
        </v-expansion-panel>


        <v-expansion-panel>
          <v-expansion-panel-title>
            Сенсоры
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-row dense>
              <v-col cols="12" sm="6" md="4">
                <StatusCard title="Температура" icon="mdi-thermometer">
                  <div v-if="status.system.sensors.temperatures !== 'not available'">
                    <ul class="sensor-block">
                      <li v-for="(items, sensor) in status.system.sensors.temperatures" :key="sensor"
                          class="sensor-group">
                        <div class="sensor-title">{{ sensor }}</div>
                        <ul>
                          <li
                            v-for="entry in items"
                            :key="entry.label"
                            class="sensor-line"
                          >
                            <span>{{ entry.label || '—' }}</span>
                            <span class="mono">{{ entry.current }}°C</span>
                          </li>
                        </ul>
                      </li>
                    </ul>
                  </div>
                  <div v-else class="text-sm">Недоступно</div>
                </StatusCard>
              </v-col>

              <v-col cols="12" sm="6" md="4">
                <StatusCard title="Вентиляторы" icon="mdi-fan">
                  <div v-if="status.system.sensors.fans !== 'not available'">
                    <ul class="sensor-block">
                      <li v-for="(items, fan) in status.system.sensors.fans" :key="fan" class="sensor-group">
                        <div class="sensor-title">{{ fan }}</div>
                        <ul>
                          <li
                            v-for="entry in items"
                            :key="entry.label"
                            class="sensor-line"
                          >
                            <span>{{ entry.label || '—' }}</span>
                            <span class="mono">{{ entry.current }} RPM</span>
                          </li>
                        </ul>
                      </li>
                    </ul>
                  </div>
                  <div v-else class="text-sm">Недоступно</div>
                </StatusCard>
              </v-col>

              <v-col cols="12" sm="6" md="4">
                <StatusCard title="Батарея" icon="mdi-battery">
                  <div v-if="status.system.sensors.battery !== 'not available'">
                    <ul class="sensor-block">
                      <li class="sensor-line">
                        <span>Заряд</span>
                        <span class="mono">{{ status.system.sensors.battery.percent }}%</span>
                      </li>
                      <li class="sensor-line">
                        <span>Подключено</span>
                        <span class="mono">{{ status.system.sensors.battery.power_plugged ? 'Да' : 'Нет' }}</span>
                      </li>
                      <li class="sensor-line">
                        <span>Осталось</span>
                        <span class="mono">{{ status.system.sensors.battery.secsleft }} сек</span>
                      </li>
                    </ul>
                  </div>
                  <div v-else class="text-sm">Недоступно</div>
                </StatusCard>
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel>
          <v-expansion-panel-title>
            Сеть ({{ status.system.network.interfaces?.length || 0 }} интерфейсов)
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-card class="pa-3 mb-4">
              <div class="font-bold text-base mb-2">
                <v-icon icon="mdi-ethernet" class="mr-1" size="18"/>
                Сетевые интерфейсы
              </div>
              <v-data-table
                :headers="ifaceHeaders"
                :items="status.system.network.interfaces"
                :items-per-page="5"
                class="elevation-1"
                item-value="name"
                dense
              >
                <template #item.type="{ item }">
                  {{ item.wifi ? 'Wi-Fi' : item.type || '—' }}
                </template>
                <template #item.ssid="{ item }">
                  {{ item.wifi?.ssid || '—' }}
                </template>
                <template #item.freq="{ item }">
                  {{ item.wifi?.channel?.channel || '—' }}
                </template>
                <template #item.txpower="{ item }">
                  {{ item.wifi?.txpower || '—' }}
                </template>
                <template #item.connection="{ item }">
                  {{ item.wifi?.type || '—' }}
                </template>
              </v-data-table>
            </v-card>


            <v-card class="pa-3 mb-4">
              <div class="flex justify-between items-center mb-2">
                <div class="font-bold text-base">
                  <v-icon icon="mdi-wifi" class="mr-1" size="18"/>
                  Доступные Wi-Fi сети ({{ status.system.network.wifi_networks?.length || 0 }})
                </div>
                <v-btn density="compact" size="small" variant="outlined" @click="status.loadWifi()">
                  Обновить Wi-Fi
                </v-btn>
              </div>

              <v-expansion-panels multiple>
                <v-expansion-panel
                  v-for="(group, ssid) in groupedWifiNetworks"
                  :key="ssid || '—'"
                >
                  <v-expansion-panel-title>
                    <div class="w-full flex justify-between items-center">
                      <div class="flex items-center gap-2 font-medium">
      <span :class="group.some(w => w.is_active) ? 'text-green-600' : ''">
        {{ ssid || 'Скрытая сеть' }}
      </span>

                        <v-icon
                          v-if="group.some(w => w.freq && w.freq < 3000)"
                          size="16"
                          color="blue-grey"
                          title="2.4 ГГц"
                        >mdi-wifi-strength-1
                        </v-icon>

                        <v-icon
                          v-if="group.some(w => w.freq && w.freq >= 5000)"
                          size="16"
                          color="deep-purple"
                          title="5 ГГц"
                        >mdi-wifi-strength-3
                        </v-icon>

                        <v-icon
                          v-if="group.every(w => w.security === 'secured')"
                          size="16"
                          color="blue"
                          title="Защищено"
                        >mdi-lock
                        </v-icon>
                      </div>

                      <div class="text-sm text-muted">
                        {{ group.length }} точк{{ group.length === 1 ? 'а' : 'и' }}, сигнал:
                        {{ Math.max(...group.map(w => w.signal_dbm || -100)) }} дБм
                      </div>
                    </div>
                  </v-expansion-panel-title>

                  <v-expansion-panel-text>
                    <v-data-table
                      :headers="wifiGroupHeaders"
                      :items="group"
                      item-value="bssid"
                      density="compact"
                      class="elevation-1"
                      :sort-by="[{ key: 'signal_dbm', order: 'desc' }]"
                    >
                      <template #item.freq="{ item }">
                        <v-icon :title="item.freq > 4900 ? '5 ГГц' : '2.4 ГГц'" size="16" class="mr-1">
                          {{ item.freq > 4900 ? 'mdi-wifi' : 'mdi-wifi-strength-2' }}
                        </v-icon>
                        {{ item.freq }} МГц
                      </template>

                      <template #item.wps="{ item }">
                        <v-icon
                          :icon="item.wps ? 'mdi-check-circle' : 'mdi-close-circle'"
                          :color="item.wps ? 'green' : 'grey'"
                          size="16"
                        />
                      </template>

                      <template #item.device="{ item }">
                        <div v-if="item.device_name || item.manufacturer || item.model">
                          <div><strong>{{ item.device_name || '—' }}</strong></div>
                          <div class="text-sm text-muted">
                            {{ item.manufacturer || '—' }} {{ item.model || '' }}
                          </div>
                          <div v-if="item.serial_number" class="text-xs">S/N: {{ item.serial_number }}</div>
                          <div v-if="item.device_type" class="text-xs">Type: {{ item.device_type }}</div>
                          <div v-if="item.wps_config_methods?.length" class="text-xs">
                            WPS: {{ item.wps_config_methods.join(', ') }}
                          </div>
                        </div>
                        <span v-else>—</span>
                      </template>
                    </v-data-table>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </v-card>

            <StatusCard title="Активные подключения" icon="mdi-connection">
              <v-data-table
                :headers="connectionHeaders"
                :items="status.system.network.connections"
                :items-per-page="10"
                class="elevation-1"
                item-value="fd"
                dense
              >
                <template #item.raddr="{ item }">
                  {{ item.raddr || '—' }}
                </template>
                <template #item.pid="{ item }">
                  {{ item.pid || '—' }}
                </template>
              </v-data-table>
            </StatusCard>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel>
          <v-expansion-panel-title>
            Docker
            <v-btn density="compact" size="small" variant="outlined" @click="status.loadDocker()">
              Обновить Docker
            </v-btn>
            <template v-if="status.docker.containers.length">
              (всего: {{ status.docker.containers?.length || 0 }},
              🟢 {{ status.docker.host?.containers.running || 0 }},
              🔴 {{ status.docker.host?.containers.stopped || 0 }},
              ⏸️ {{ status.docker.host?.containers.paused || 0 }})
            </template>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-row class="mb-2 info_panel">
              <v-col cols="12" sm="6" md="3">
                <StatusCard title="Docker Version" icon="mdi-docker" class="docker-card">
                  {{ status.docker.host.docker_version }}
                </StatusCard>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <StatusCard title="API Version" icon="mdi-api" class="docker-card">
                  {{ status.docker.host.api_version }}
                </StatusCard>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <StatusCard title="OS" icon="mdi-linux" class="docker-card">
                  {{ status.docker.host.os }}
                </StatusCard>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <StatusCard title="Arch" icon="mdi-chip" class="docker-card">
                  {{ status.docker.host.arch }}
                </StatusCard>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <StatusCard title="Образов" icon="mdi-database" class="docker-card">
                  {{ status.docker.host.images }}
                </StatusCard>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <StatusCard title="Storage Driver" icon="mdi-harddisk" class="docker-card">
                  {{ status.docker.host.storage_driver }}
                </StatusCard>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <StatusCard title="Network Driver" icon="mdi-ethernet" class="docker-card">
                  {{ status.docker.host.network_driver || '—' }}
                </StatusCard>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <StatusCard title="Volumes" icon="mdi-database-check" class="docker-card">
                  <template v-if="Array.isArray(status.docker.host.volumes)">
                    {{ status.docker.host.volumes.length }}<br/>
                    {{ status.docker.host.volumes.join(', ') }}
                  </template>
                  <template v-else>
                    {{ status.docker.host.volumes || '—' }}
                  </template>
                </StatusCard>
              </v-col>
            </v-row>

            <v-row>
              <v-col cols="12">
                <StatusCard title="Plugins" icon="mdi-puzzle">
                  <v-row dense>
                    <v-col
                      v-for="(items, type) in status.docker.host.plugins"
                      :key="type"
                      cols="12"
                      sm="6"
                      md="4"
                    >
                      <div class="font-medium capitalize mb-1">{{ type }}:</div>
                      <v-chip
                        v-for="plugin in items || []"
                        :key="plugin"
                        class="ma-1"
                        size="small"
                        color="blue-grey-lighten-3"
                        label
                      >
                        {{ plugin }}
                      </v-chip>
                    </v-col>
                  </v-row>
                </StatusCard>
              </v-col>
            </v-row>

            <v-row dense class="gap-4">
              <v-col
                v-for="container in [...status.docker.containers].sort((a, b) => b.status === 'running' ? 1 : -1)"
                :key="container.id"
                cols="12"
                sm="6"
                md="3"
              >
                <v-card class="docker-card" elevation="1">
                  <div class="font-bold text-base mb-1">
                    <v-icon start icon="mdi-docker" size="18" class="mr-1"/>
                    {{ container.name }}
                    <v-chip
                      size="x-small"
                      :color="container.status === 'running' ? 'green' : 'grey'"
                      class="ml-2"
                    >
                      {{ container.status }}
                    </v-chip>
                  </div>
                  <div class="text-sm mb-1">
                    Образ: {{ container.image?.[0] || '—' }}<br/>
                    Аптайм: {{ formatDate(container.uptime) }}
                  </div>
                  <div v-if="container.status === 'running'" class="text-sm mb-1">
                    CPU: {{ container.cpu_usage_percent }}%<br/>
                    Память: {{ container.memory_usage }}<br/>
                    Лимиты: {{ container.resources?.cpu_limit || '—' }} /
                    {{ formatBytes(container.resources?.mem_limit || 0) }}
                  </div>
                  <div v-if="container.mounts?.length" class="text-sm mb-1">
            <span class="mounts-toggle" @click="container.showMounts = !container.showMounts">
              <v-icon size="14" class="mr-1">{{
                  container.showMounts ? 'mdi-chevron-down' : 'mdi-chevron-right'
                }}</v-icon>
              Точни монтирования ({{ container.mounts.length }})
            </span>
                    <ul v-if="container.showMounts" class="no-bullets ml-4 mt-1 ul_small_no_wrap">
                      <li v-for="m in container.mounts" :key="m">{{ m }}</li>
                    </ul>
                  </div>
                  <div v-if="container.open_ports?.length" class="text-sm">
                    Порты:
                    <ul class="no-bullets ml-2">
                      <li
                        v-for="port in container.open_ports"
                        :key="port.container_port"
                        :class="port.status === 'open' ? 'text-green-600' : 'text-red-500'"
                      >
                        <v-icon
                          :icon="port.status === 'open' ? 'mdi-check-circle' : 'mdi-close-circle'"
                          size="14"
                          class="mr-1"
                        />
                        {{ port.container_port }} → {{ port.host_ip }}:{{ port.host_port }} ({{ port.status }})
                      </li>
                    </ul>
                  </div>
                </v-card>
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>

      </v-expansion-panels>
    </div>
  </div>
</template>


<script setup lang="ts">
import {onMounted, ref, watch} from 'vue'
import {useStatusStore} from '@/store/statusStore'
import StatusCard from '@/components/StatusCard.vue'
import LineChart from '@/components/LineChart.vue'

const status = useStatusStore()
const refreshInterval = ref<number | null>(null)
const intervalOptions = [
  {label: '1с', value: 1000},
  {label: '5с', value: 5000},
  {label: '15с', value: 15000},
  {label: '30с', value: 30000},
  {label: '1м', value: 60000}
]
let timer: number | null = null
const preserveUI = ref(false)
const cooldown = ref(false)

const cpuHistory = ref<number[][]>([])
const cpuLabels = ref<string[]>([])
const memoryHistory = ref<number[]>([])
const timestampLabels = ref<string[]>([])

const userHeaders = [
  {title: 'Пользователь', value: 'name', sortable: true},
  {title: 'PID', value: 'pid', sortable: true},
  {title: 'Терминал', value: 'terminal', sortable: true},
  {title: 'Хост', value: 'host', sortable: true},
  {title: 'Сессия началась', value: 'started', sortable: true}
]

const processHeaders = [
  {title: 'PID', value: 'pid', sortable: true},
  {title: 'Имя', value: 'name', sortable: true},
  {title: 'Пользователь', value: 'username', sortable: true},
  {title: 'CPU (%)', value: 'cpu_percent', sortable: true},
  {title: 'Память (%)', value: 'memory_percent', sortable: true},
  {title: 'Память (МБ)', value: 'memory_info.rss', sortable: false},
  {title: 'Статус', value: 'status', sortable: true},
  {title: 'Создан', value: 'create_time', sortable: true},
  {title: 'Команда', value: 'cmdline', sortable: false}
]

const ifaceHeaders = [
  {title: 'Имя', value: 'name', sortable: true},
  {title: 'Тип', value: 'type', sortable: true},
  {title: 'MAC', value: 'mac'},
  {title: 'IP', value: 'ip'},
  {title: 'Маска', value: 'mask'},
  {title: 'SSID', value: 'ssid'},
  {title: 'Частота', value: 'freq'},
  {title: 'TxPower', value: 'txpower'},
  {title: 'Сеть', value: 'connection'}
]


const wifiGroupHeaders = [
  {title: 'BSSID', value: 'bssid', sortable: true},
  {title: 'Частота', value: 'freq', sortable: true},
  {title: 'Канал', value: 'channel', sortable: true},
  {title: 'Сигнал (dBm)', value: 'signal_dbm', sortable: true},
  {title: 'Защита', value: 'security', sortable: true},
  {title: 'WPS', value: 'wps', sortable: true},
  {title: 'boottime', value: 'boottime', sortable: true},
  {title: 'last_seen_ms', value: 'last_seen_ms', sortable: true},
  {title: 'Устройство', value: 'device', sortable: false}
]


const connectionHeaders = [
  {title: 'Локальный адрес', value: 'laddr'},
  {title: 'Удалённый адрес', value: 'raddr'},
  {title: 'Статус', value: 'status'},
  {title: 'PID', value: 'pid'}
]

const groupedWifiNetworks = computed(() => {
  const result = {}
  for (const net of status.system.network.wifi_networks || []) {
    const key = net.ssid || ''
    if (!result[key]) result[key] = []
    result[key].push(net)
  }
  return result
})


function loadStatus(reset = true) {
  if (cooldown.value) return
  cooldown.value = true
  setTimeout(() => (cooldown.value = false), 1000)

  preserveUI.value = !reset
  status.loadStatus().then(() => {
    const cpuSlice = status.system.cpu.per_core_usage_percent
    cpuHistory.value.push(cpuSlice)
    cpuLabels.value = cpuSlice.map((_, i) => `Core ${i + 1}`)
    if (cpuHistory.value.length > 20) cpuHistory.value.shift()

    memoryHistory.value.push(status.system.memory.percent)
    if (memoryHistory.value.length > 20) memoryHistory.value.shift()

    const now = new Date()
    timestampLabels.value.push(now.toLocaleTimeString())
    if (timestampLabels.value.length > 20) timestampLabels.value.shift()

    preserveUI.value = false
  })
}

onMounted(() => {
  const load_data = [
    [loadStatus, false],
    [status.loadDocker],
    [status.loadWifi],
  ]
  for (const load_item of load_data) {
    const fn = load_item.shift()
    setTimeout(fn, 10, ...load_item)
  }
})

watch(refreshInterval, (newVal) => {
  if (timer) clearInterval(timer)
  if (newVal) {
    timer = setInterval(() => loadStatus(false), newVal)
  }
})

function formatBytes(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  const units = ['KB', 'MB', 'GB', 'TB']
  let i = -1
  do {
    bytes /= 1024
    i++
  } while (bytes >= 1024 && i < units.length - 1)
  return bytes.toFixed(1) + ' ' + units[i]
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}

function formatUptime(minutes: number): string {
  const days = Math.floor(minutes / 1440)
  const hours = Math.floor((minutes % 1440) / 60)
  const mins = minutes % 60

  const parts = []
  if (days > 0) parts.push(`${days} дн`)
  if (hours > 0) parts.push(`${hours} ч`)
  if (mins > 0 || parts.length === 0) parts.push(`${mins} мин`)

  return parts.join(', ')
}
</script>

<style scoped>
pre {
  white-space: pre-wrap;
  word-break: break-word;
}

.text-green-600 {
  color: #16a34a;
}

.text-red-500 {
  color: #ef4444;
}

ul.no-bullets {
  list-style: none;
  padding-left: 0;
  margin: 0;
}

.v-card.docker-card {
  padding: 12px;
  margin-bottom: 8px;
}

.mounts-toggle {
  cursor: pointer;
  color: #1976d2;
  font-size: 13px;
  margin-top: 4px;
}

.info_panel > div {
  padding: 0 5px;
}

.ul_small_no_wrap li {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 0.8em;
}

.ul_small_no_wrap li:before {
  content: ' ';
  background: #1976d2;
  height: 10px;
  width: 10px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 5px;
}

.text-xxs {
  font-size: 0.65rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.v-progress-linear .v-progress-linear__content {
  padding: 0 !important;
}

.v-simple-table {
  font-size: 0.85rem;
}

.v-simple-table th {
  font-weight: 600;
  white-space: nowrap;
}

.v-simple-table td {
  white-space: nowrap;
  padding: 4px 8px;
}

.disk_wrap {
  height: 100%;
  width: 100%;
}

.partition_wrap {
  position: relative;
}

.partition_percent {
  width: 12.74%;
  background: #999;
  position: absolute;
  height: 100%;
  opacity: 0.7;
  border-radius: 2px;
  transition: width 0.3s ease;
  left: 0;
}

.partition_label {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  text-align: center;
  font-size: 0.7em;
  color: #fff;
  font-weight: 600;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
  z-index: 1;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sensor-block {
  list-style: none;
  padding: 0;
  margin: 0;
  border-bottom: 1px solid #999;
}

.sensor-title {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 4px;
}

.sensor-line {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  padding: 2px 20px;
  border-bottom: 1px dashed #ccc;
}

.sensor-group {
  border-bottom: 1px dashed #222;
}

.sensor-group:last-child {
  border-bottom: none;
}

.sensor-line:last-child {
  border-bottom: none;
}

.mono {
  font-family: monospace;
}
</style>
