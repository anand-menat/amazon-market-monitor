<script setup>
import { computed, ref, watch } from 'vue'
import { LineChart, RefreshCcw, Sparkles, TrendingDown, TrendingUp } from 'lucide-vue-next'
import { api } from '../services/api'
import PriceHistoryChart from './PriceHistoryChart.vue'

const props = defineProps({
  product: {
    type: Object,
    required: true
  },
  refreshKey: Number
})

const emit = defineEmits(['refresh-products'])
const loading = ref(false)
const analysisLoading = ref(false)
const detailLoading = ref(false)
const competitors = ref([])
const priceHistory = ref([])
const analysis = ref(null)
const error = ref('')

const toNumber = (value) => {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(String(value).replace(/[^0-9.-]/g, ''))
  return Number.isFinite(parsed) ? parsed : null
}

const formatMoney = (value, currency = props.product.currency) => {
  const number = toNumber(value)
  if (number === null) return '-'
  return `${currency || ''} ${number.toFixed(2)}`.trim()
}

const formatDate = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

const comparison = computed(() => {
  const productPrice = toNumber(props.product.price)
  const pricedCompetitors = competitors.value
    .map((item) => ({ ...item, numericPrice: toNumber(item.price) }))
    .filter((item) => item.numericPrice !== null)
    .sort((a, b) => a.numericPrice - b.numericPrice)

  const cheapest = pricedCompetitors[0] || null
  const average =
    pricedCompetitors.length > 0
      ? pricedCompetitors.reduce((sum, item) => sum + item.numericPrice, 0) / pricedCompetitors.length
      : null
  const undercutCount =
    productPrice === null ? 0 : pricedCompetitors.filter((item) => item.numericPrice < productPrice).length

  return {
    productPrice,
    cheapest,
    average,
    undercutCount,
    pricedCount: pricedCompetitors.length
  }
})

const ratingLeader = computed(() => {
  const productRating = toNumber(props.product.rating)
  const ratedCompetitors = competitors.value
    .map((item) => ({ ...item, numericRating: toNumber(item.rating) }))
    .filter((item) => item.numericRating !== null)
    .sort((a, b) => b.numericRating - a.numericRating)

  const leader = ratedCompetitors[0] || null
  return {
    leader,
    productRating,
    gap: leader && productRating !== null ? leader.numericRating - productRating : null
  }
})

const historyTrend = computed(() => {
  const points = priceHistory.value
    .map((item) => ({ ...item, numericPrice: toNumber(item.price) }))
    .filter((item) => item.numericPrice !== null)

  if (points.length < 2) return null
  const latest = points[0]
  const previous = points[1]
  return {
    latest,
    previous,
    delta: latest.numericPrice - previous.numericPrice
  }
})

const loadDetails = async () => {
  if (!props.product?.asin) return
  detailLoading.value = true
  error.value = ''
  analysis.value = null
  try {
    const [competitorData, historyData] = await Promise.all([
      api.getCompetitors(props.product.asin),
      api.getPriceHistory(props.product.asin, 30)
    ])
    competitors.value = competitorData.items || []
    priceHistory.value = historyData.items || []
  } catch (err) {
    error.value = err.message
  } finally {
    detailLoading.value = false
  }
}

const fetchCompetitors = async () => {
  loading.value = true
  error.value = ''
  try {
    competitors.value = await api.fetchCompetitors(props.product.asin, {
      domain: props.product.amazon_domain || 'com',
      country_code: props.product.country_code || 'us',
      pages: 2
    })
    const historyData = await api.getPriceHistory(props.product.asin, 30)
    priceHistory.value = historyData.items || []
    emit('refresh-products')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const analyze = async () => {
  analysisLoading.value = true
  error.value = ''
  try {
    const result = await api.analyzeProduct(props.product.asin)
    analysis.value = result
  } catch (err) {
    error.value = err.message
  } finally {
    analysisLoading.value = false
  }
}

watch(() => [props.product.asin, props.refreshKey], loadDetails, { immediate: true })
</script>

<template>
  <section class="detail-panel">
    <div class="section-heading">
      <div>
        <p class="panel-kicker">Selected ASIN {{ product.asin }}</p>
        <h2>Competitor workflow</h2>
      </div>
      <div class="actions">
        <button @click="fetchCompetitors" :disabled="loading">
          <RefreshCcw :size="17" />
          {{ loading ? 'Fetching...' : 'Fetch' }}
        </button>
        <button class="primary-button small" @click="analyze" :disabled="analysisLoading">
          <Sparkles :size="17" />
          {{ analysisLoading ? 'Analyzing...' : 'Analyze' }}
        </button>
      </div>
    </div>

    <div v-if="error" class="notice error">{{ error }}</div>

    <div v-if="detailLoading" class="empty-state compact">Loading competitor context...</div>

    <div v-else-if="competitors.length" class="insight-grid">
      <div class="insight-card">
        <span class="panel-kicker">Price position</span>
        <strong>
          {{ comparison.undercutCount }}
          <small>below your price</small>
        </strong>
        <p>
          Cheapest:
          <span v-if="comparison.cheapest">
            {{ comparison.cheapest.asin }} at {{ formatMoney(comparison.cheapest.price, comparison.cheapest.currency) }}
          </span>
          <span v-else>-</span>
        </p>
      </div>

      <div class="insight-card">
        <span class="panel-kicker">Market average</span>
        <strong>{{ formatMoney(comparison.average) }}</strong>
        <p>{{ comparison.pricedCount }} competitors with comparable price data</p>
      </div>

      <div class="insight-card">
        <span class="panel-kicker">Rating leader</span>
        <strong>{{ ratingLeader.leader?.rating || '-' }}</strong>
        <p>
          <span v-if="ratingLeader.leader">
            {{ ratingLeader.leader.asin }}
            <template v-if="ratingLeader.gap !== null"> leads by {{ ratingLeader.gap.toFixed(1) }}</template>
          </span>
          <span v-else>No rating data yet</span>
        </p>
      </div>
    </div>

    <div v-if="priceHistory.length > 0" class="chart-section">
      <div class="metric-strip history-strip" v-if="historyTrend">
        <span>
          <TrendingUp v-if="historyTrend.delta > 0" :size="18" />
          <TrendingDown v-else :size="18" />
          Latest scrape moved {{ formatMoney(Math.abs(historyTrend.delta)) }}
          {{ historyTrend.delta > 0 ? 'up' : 'down' }}
        </span>
        <span>{{ formatDate(historyTrend.latest.scraped_at) }}</span>
      </div>
      <PriceHistoryChart :data="priceHistory" :currency="product.currency" />
    </div>

    <div v-if="!detailLoading && competitors.length" class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ASIN</th>
            <th>Title</th>
            <th>Price</th>
            <th>Rating</th>
            <th>Gap</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in competitors" :key="item.asin">
            <td>{{ item.asin }}</td>
            <td>{{ item.title || '-' }}</td>
            <td>{{ item.currency || '' }} {{ item.price || '-' }}</td>
            <td>{{ item.rating || '-' }}</td>
            <td>
              <span v-if="comparison.productPrice !== null && toNumber(item.price) !== null">
                {{ formatMoney(toNumber(item.price) - comparison.productPrice, item.currency || product.currency) }}
              </span>
              <span v-else>-</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="!detailLoading && !competitors.length" class="metric-strip">
      <span><LineChart :size="18" /> Competitors appear here after a run.</span>
    </div>

    <section v-if="analysis" class="analysis-panel">
      <div>
        <p class="panel-kicker">AI readout</p>
        <h3>{{ analysis.summary }}</h3>
        <p>{{ analysis.positioning }}</p>
      </div>

      <div v-if="analysis.top_competitors?.length" class="analysis-list">
        <article v-for="item in analysis.top_competitors.slice(0, 4)" :key="item.asin">
          <strong>{{ item.asin }}</strong>
          <span>{{ item.title || 'Competitor' }}</span>
          <small>{{ item.currency || '' }} {{ item.price || '-' }} | Rating {{ item.rating || '-' }}</small>
          <ul v-if="item.key_points?.length">
            <li v-for="point in item.key_points" :key="point">{{ point }}</li>
          </ul>
        </article>
      </div>

      <div v-if="analysis.recommendations?.length" class="recommendation-list">
        <p class="panel-kicker">Recommended actions</p>
        <ul>
          <li v-for="recommendation in analysis.recommendations" :key="recommendation">
            {{ recommendation }}
          </li>
        </ul>
      </div>
    </section>
  </section>
</template>
