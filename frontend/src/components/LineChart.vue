<template>
  <div>
    <component :is="chartTypeComponent" :data="chartData" :options="chartOptions"/>
  </div>
</template>

<script setup lang="ts">
import {computed} from 'vue'
import {Line, Bar} from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  LineElement,
  BarElement,
  PointElement,
  LinearScale,
  CategoryScale
} from 'chart.js'

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  LineElement,
  BarElement,
  PointElement,
  LinearScale,
  CategoryScale
)

const props = defineProps<{
  data: number[] | number[][]
  label: string | string[]
  xLabels?: string[]
  type?: 'line' | 'bar'
  showPoints?: boolean
  lineWidth?: number
  axisSwap?: boolean // true => X <-> Y
}>()

const chartTypeComponent = computed(() => {
  return props.type === 'bar' ? Bar : Line
})

function generateColor(index: number): string {
  const hue = (index * 137.508) % 360 // use golden angle approximation
  return `hsl(${hue}, 70%, 50%)`
}

const chartData = computed(() => {
  const isMulti = Array.isArray(props.data[0])

  const data = props.axisSwap && isMulti ? props.data[0].map((_, i) => props.data.map(row => row[i])) : props.data

  const datasets = isMulti
    ? (data as number[][]).map((dataset, i) => {
      const color = generateColor(i)
      return {
        label: Array.isArray(props.label) ? props.label[i] : `Series ${i + 1}`,
        data: dataset,
        tension: 0.4,
        fill: false,
        borderColor: color,
        backgroundColor: color,
        borderWidth: props.lineWidth ?? 2,
        pointRadius: props.showPoints === false ? 0 : 3,
      }
    })
    : [
      {
        label: props.label as string,
        data: props.data as number[],
        tension: 0.4,
        fill: false,
        borderColor: generateColor(0),
        backgroundColor: generateColor(0),
        borderWidth: props.lineWidth ?? 2,
        pointRadius: props.showPoints === false ? 0 : 4,
      }
    ]

  const labels = props.xLabels
    ? props.xLabels
    : isMulti
      ? (props.data as number[][])[0].map((_, i) => i + 1)
      : (props.data as number[]).map((_, i) => i + 1)

  return {
    labels: labels,
    datasets: datasets
  }
})

const chartOptions = computed(() => {
  const base = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {display: true},
    },
    indexAxis: 'x',
    scales: {
      x: {beginAtZero: true},
      y: {beginAtZero: true}
    }
  }
  return base
})
</script>

<style scoped>
div {
  width: 100%;
  height: 200px;
}
</style>
