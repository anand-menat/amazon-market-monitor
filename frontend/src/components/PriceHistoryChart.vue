<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  data: {
    type: Array,
    required: true
  },
  currency: {
    type: String,
    default: ''
  }
})

const containerRef = ref(null)
const width = ref(600)
const height = ref(200)
const padding = { top: 20, right: 20, bottom: 30, left: 50 }
const hoveredIndex = ref(null)

const updateDimensions = () => {
  if (containerRef.value) {
    width.value = containerRef.value.clientWidth
  }
}

onMounted(() => {
  updateDimensions()
  window.addEventListener('resize', updateDimensions)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateDimensions)
})

const sortedData = computed(() => {
  return [...props.data]
    .map(d => ({
      ...d,
      timestamp: new Date(d.scraped_at).getTime(),
      priceNum: parseFloat(d.price)
    }))
    .filter(d => !isNaN(d.priceNum))
    .sort((a, b) => a.timestamp - b.timestamp)
})

const scales = computed(() => {
  if (sortedData.value.length === 0) return null

  const data = sortedData.value
  const minTime = data[0].timestamp
  const maxTime = data[data.length - 1].timestamp
  const minPrice = Math.min(...data.map(d => d.priceNum))
  const maxPrice = Math.max(...data.map(d => d.priceNum))

  // Add 10% padding to price scale
  const pricePadding = (maxPrice - minPrice) * 0.1 || maxPrice * 0.1
  const paddedMinPrice = Math.max(0, minPrice - pricePadding)
  const paddedMaxPrice = maxPrice + pricePadding

  const timeRange = Math.max(1, maxTime - minTime)
  const priceRange = Math.max(0.1, paddedMaxPrice - paddedMinPrice)

  const innerWidth = width.value - padding.left - padding.right
  const innerHeight = height.value - padding.top - padding.bottom

  return {
    x: (time) => padding.left + ((time - minTime) / timeRange) * innerWidth,
    y: (price) => padding.top + innerHeight - ((price - paddedMinPrice) / priceRange) * innerHeight,
    minTime,
    maxTime,
    minPrice: paddedMinPrice,
    maxPrice: paddedMaxPrice
  }
})

const points = computed(() => {
  if (!scales.value) return []
  return sortedData.value.map(d => ({
    x: scales.value.x(d.timestamp),
    y: scales.value.y(d.priceNum),
    ...d
  }))
})

const linePath = computed(() => {
  if (points.value.length === 0) return ''
  const path = points.value.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`)
  return path.join(' ')
})

const areaPath = computed(() => {
  if (points.value.length === 0) return ''
  const innerHeight = height.value - padding.bottom
  const path = `${linePath.value} L ${points.value[points.value.length - 1].x} ${innerHeight} L ${points.value[0].x} ${innerHeight} Z`
  return path
})

const yAxisLabels = computed(() => {
  if (!scales.value) return []
  const { minPrice, maxPrice } = scales.value
  const steps = 4
  const step = (maxPrice - minPrice) / steps
  return Array.from({ length: steps + 1 }).map((_, i) => minPrice + step * i)
})

const xAxisLabels = computed(() => {
  if (points.value.length === 0) return []
  // Show at most 5 labels, roughly evenly spaced
  const maxLabels = 5
  const step = Math.ceil(points.value.length / maxLabels)
  return points.value.filter((_, i) => i % step === 0 || i === points.value.length - 1)
})

const formatDate = (timestamp) => {
  const d = new Date(timestamp)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${d.getMinutes().toString().padStart(2, '0')}`
}
</script>

<template>
  <div class="chart-container" ref="containerRef" v-if="sortedData.length > 0">
    <svg :width="width" :height="height" class="chart-svg">
      <defs>
        <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#237872" stop-opacity="0.2" />
          <stop offset="100%" stop-color="#237872" stop-opacity="0" />
        </linearGradient>
      </defs>

      <!-- Y Axis Grid Lines -->
      <g class="grid-lines">
        <line
          v-for="val in yAxisLabels"
          :key="val"
          :x1="padding.left"
          :y1="scales.y(val)"
          :x2="width - padding.right"
          :y2="scales.y(val)"
        />
      </g>

      <!-- Area and Line -->
      <path :d="areaPath" fill="url(#areaGradient)" class="chart-area" />
      <path :d="linePath" fill="none" class="chart-line" />

      <!-- Data Points -->
      <g class="data-points">
        <circle
          v-for="(p, i) in points"
          :key="i"
          :cx="p.x"
          :cy="p.y"
          r="4"
          @mouseenter="hoveredIndex = i"
          @mouseleave="hoveredIndex = null"
          :class="{ hovered: hoveredIndex === i }"
        />
      </g>

      <!-- Y Axis Labels -->
      <g class="y-labels">
        <text
          v-for="val in yAxisLabels"
          :key="val"
          :x="padding.left - 8"
          :y="scales.y(val)"
          alignment-baseline="middle"
          text-anchor="end"
        >
          {{ props.currency }}{{ val.toFixed(0) }}
        </text>
      </g>

      <!-- X Axis Labels -->
      <g class="x-labels">
        <text
          v-for="p in xAxisLabels"
          :key="p.timestamp"
          :x="p.x"
          :y="height - 10"
          text-anchor="middle"
        >
          {{ formatDate(p.timestamp) }}
        </text>
      </g>
    </svg>

    <!-- Tooltip -->
    <div
      v-if="hoveredIndex !== null"
      class="chart-tooltip"
      :style="{
        left: `${points[hoveredIndex].x}px`,
        top: `${points[hoveredIndex].y - 10}px`
      }"
    >
      <div class="tooltip-price">{{ props.currency }}{{ points[hoveredIndex].priceNum.toFixed(2) }}</div>
      <div class="tooltip-date">{{ formatDate(points[hoveredIndex].timestamp) }}</div>
    </div>
  </div>
  <div v-else class="empty-state compact">
    Not enough data points for chart.
  </div>
</template>
