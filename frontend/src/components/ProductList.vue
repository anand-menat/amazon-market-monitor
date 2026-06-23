<script setup>
import { computed, ref } from 'vue'
import ProductCard from './ProductCard.vue'

const props = defineProps({
  products: {
    type: Array,
    default: () => []
  },
  pagination: Object,
  loading: Boolean,
  selectedAsin: String
})

defineEmits(['select', 'delete', 'clear', 'page'])

const search = ref('')
const sortBy = ref('updated')

const toNumber = (value) => {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(String(value).replace(/[^0-9.-]/g, ''))
  return Number.isFinite(parsed) ? parsed : null
}

const visibleProducts = computed(() => {
  const term = search.value.trim().toLowerCase()
  const filtered = term
    ? props.products.filter((product) =>
        [product.title, product.brand, product.asin, product.country_code]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(term))
      )
    : [...props.products]

  return filtered.sort((first, second) => {
    if (sortBy.value === 'price_low') {
      return (toNumber(first.price) ?? Number.MAX_SAFE_INTEGER) - (toNumber(second.price) ?? Number.MAX_SAFE_INTEGER)
    }
    if (sortBy.value === 'rating_high') {
      return (toNumber(second.rating) ?? -1) - (toNumber(first.rating) ?? -1)
    }
    return String(second.updated_at || second.created_at || '').localeCompare(
      String(first.updated_at || first.created_at || '')
    )
  })
})
</script>

<template>
  <section class="product-section">
    <div class="section-heading">
      <div>
        <p class="panel-kicker">Stored products</p>
        <h2>Scrape results</h2>
      </div>
      <span class="count-pill">{{ pagination.total }} records</span>
    </div>

    <div v-if="products.length" class="list-controls">
      <input v-model="search" placeholder="Search title, brand, ASIN, country" />
      <select v-model="sortBy">
        <option value="updated">Latest updated</option>
        <option value="price_low">Price low to high</option>
        <option value="rating_high">Rating high to low</option>
      </select>
      <button @click="$emit('clear')" class="danger-btn" style="margin-left: auto;">Clear All</button>
    </div>

    <div v-if="loading && !products.length" class="empty-state">Loading products...</div>
    <div v-else-if="!products.length" class="empty-state">No products scraped yet.</div>
    <div v-else-if="!visibleProducts.length" class="empty-state">No products match your filters.</div>

    <div v-else class="product-grid">
      <ProductCard
        v-for="product in visibleProducts"
        :key="product.asin"
        :product="product"
        :selected="selectedAsin === product.asin"
        @select="$emit('select', product)"
        @delete="$emit('delete', product)"
      />
    </div>

    <div v-if="pagination.total_pages > 1" class="pagination">
      <button :disabled="pagination.page <= 1" @click="$emit('page', pagination.page - 1)">Previous</button>
      <span>Page {{ pagination.page }} of {{ pagination.total_pages }}</span>
      <button :disabled="pagination.page >= pagination.total_pages" @click="$emit('page', pagination.page + 1)">Next</button>
    </div>
  </section>
</template>
