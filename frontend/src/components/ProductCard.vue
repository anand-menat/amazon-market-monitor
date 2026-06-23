<script setup>
import { BarChart3, CheckCircle2, Trash2 } from 'lucide-vue-next'

defineProps({
  product: {
    type: Object,
    required: true
  },
  selected: Boolean
})

const firstImage = (product) => product.images?.[0]
defineEmits(['select', 'delete'])
</script>

<template>
  <article class="product-card" :class="{ selected }" @click="$emit('select')">
    <div class="product-image">
      <img v-if="firstImage(product)" :src="firstImage(product)" :alt="product.title || product.asin" />
      <BarChart3 v-else :size="32" />
    </div>

    <div class="product-body">
      <div class="card-title-row">
        <h3>{{ product.title || product.asin }}</h3>
        <div class="card-actions">
          <button
            class="remove-product"
            :title="`Remove ${product.asin}`"
            @click.stop="$emit('delete')"
          >
            <Trash2 :size="15" />
          </button>
          <CheckCircle2 v-if="selected" :size="18" />
        </div>
      </div>
      <p class="muted">{{ product.brand || 'Unknown brand' }} | {{ product.asin }}</p>

      <div class="stat-row">
        <span>{{ product.currency || '' }} {{ product.price || '-' }}</span>
        <span>Rating {{ product.rating || '-' }}</span>
        <span>{{ product.country_code?.toUpperCase() || '-' }}</span>
      </div>
    </div>
  </article>
</template>
