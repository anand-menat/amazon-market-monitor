<script setup>
import { onMounted, ref } from 'vue'
import AppHeader from './components/AppHeader.vue'
import CompetitorPanel from './components/CompetitorPanel.vue'
import ProductForm from './components/ProductForm.vue'
import ProductList from './components/ProductList.vue'
import { api } from './services/api'

const products = ref([])
const pagination = ref({ page: 1, per_page: 10, total: 0, total_pages: 0 })
const selectedProduct = ref(null)
const detailRefreshKey = ref(0)
const loading = ref(false)
const message = ref('')
const error = ref('')

const loadProducts = async (page = 1) => {
  loading.value = true
  error.value = ''
  try {
    const data = await api.getProducts(page, pagination.value.per_page)
    products.value = data.items
    pagination.value = data
    if (!selectedProduct.value && data.items.length) {
      selectedProduct.value = data.items[0]
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const handleScrape = async (payload) => {
  loading.value = true
  message.value = ''
  error.value = ''
  try {
    const result = await api.runProductWorkflow(payload)
    const product = result.product
    selectedProduct.value = product
    detailRefreshKey.value += 1
    message.value = payload.with_competitors
      ? `Scraped ${product.asin} and found ${result.competitors_found} similar products`
      : `Scraped ${product.asin}`
    await loadProducts(1)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const handleDeleteProduct = async (product) => {
  if (!confirm(`Remove ${product.asin} and its stored competitors?`)) return

  loading.value = true
  message.value = ''
  error.value = ''
  try {
    await api.deleteProduct(product.asin)
    if (selectedProduct.value?.asin === product.asin) {
      selectedProduct.value = null
    }
    message.value = `Removed ${product.asin}`
    await loadProducts(pagination.value.page)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const handleClearAll = async () => {
  if (!confirm('Are you sure you want to delete ALL products and their history? This cannot be undone.')) return

  loading.value = true
  message.value = ''
  error.value = ''
  try {
    const result = await api.clearAllProducts()
    selectedProduct.value = null
    message.value = `Removed ${result.deleted} products`
    await loadProducts(1)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(() => loadProducts())
</script>

<template>
  <main class="shell">
    <AppHeader />

    <section class="workspace">
      <aside class="left-rail">
        <ProductForm :loading="loading" @submit="handleScrape" />
      </aside>

      <section class="content-area">
        <div v-if="message" class="notice success">{{ message }}</div>
        <div v-if="error" class="notice error">{{ error }}</div>

        <ProductList
          :products="products"
          :pagination="pagination"
          :loading="loading"
          :selected-asin="selectedProduct?.asin"
          @select="selectedProduct = $event"
          @delete="handleDeleteProduct"
          @clear="handleClearAll"
          @page="loadProducts"
        />

        <CompetitorPanel
          v-if="selectedProduct"
          :product="selectedProduct"
          :refresh-key="detailRefreshKey"
          @refresh-products="loadProducts(pagination.page)"
        />
      </section>
    </section>
  </main>
</template>
