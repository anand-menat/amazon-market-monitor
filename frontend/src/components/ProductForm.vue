<script setup>
import { reactive, watch } from 'vue'
import { Search } from 'lucide-vue-next'

defineProps({
  loading: Boolean
})

const emit = defineEmits(['submit'])
const form = reactive({
  product_input: '',
  domain: 'com',
  country_code: 'us',
  with_competitors: true,
  pages: 2
})
const countryDomains = {
  us: 'com',
  ca: 'ca',
  gb: 'co.uk',
  de: 'de',
  fr: 'fr',
  it: 'it',
  in: 'in',
  ae: 'ae'
}

watch(
  () => form.country_code,
  (country) => {
    form.domain = countryDomains[country] || 'com'
  }
)

const submit = () => {
  const productInput = form.product_input.trim()
  if (!productInput) return

  const payload = {
    domain: form.domain,
    country_code: form.country_code,
    with_competitors: form.with_competitors,
    pages: Number(form.pages)
  }

  if (productInput.startsWith('http')) {
    payload.product_url = productInput
  } else {
    payload.asin = productInput
  }

  emit('submit', payload)
}
</script>

<template>
  <form class="panel form-panel" @submit.prevent="submit">
    <div>
      <p class="panel-kicker">Scrape product</p>
      <h2>Product intake</h2>
    </div>

    <label>
      <span>Amazon URL or ASIN</span>
      <input v-model="form.product_input" placeholder="https://www.amazon.com/dp/B087DFLF9S" />
    </label>

    <div class="field-grid">
      <label>
        <span>Domain</span>
        <select v-model="form.domain">
          <option value="com">amazon.com</option>
          <option value="ca">amazon.ca</option>
          <option value="co.uk">amazon.co.uk</option>
          <option value="de">amazon.de</option>
          <option value="fr">amazon.fr</option>
          <option value="it">amazon.it</option>
          <option value="in">amazon.in</option>
          <option value="ae">amazon.ae</option>
        </select>
      </label>

      <label>
        <span>Country</span>
        <select v-model="form.country_code">
          <option value="us">US</option>
          <option value="ca">CA</option>
          <option value="gb">GB</option>
          <option value="de">DE</option>
          <option value="fr">FR</option>
          <option value="it">IT</option>
          <option value="in">IN</option>
          <option value="ae">AE</option>
        </select>
      </label>
    </div>

    <label class="checkbox-row">
      <input v-model="form.with_competitors" type="checkbox" />
      <span>Automatically find similar products</span>
    </label>

    <label v-if="form.with_competitors">
      <span>Search depth</span>
      <select v-model="form.pages">
        <option :value="1">Fast scan - 1 page</option>
        <option :value="2">Balanced - 2 pages</option>
        <option :value="3">Broader - 3 pages</option>
        <option :value="5">Deep scan - 5 pages</option>
      </select>
    </label>

    <button class="primary-button" :disabled="loading || !form.product_input">
      <Search :size="18" />
      {{ loading ? 'Running...' : 'Scrape and compare' }}
    </button>
  </form>
</template>
