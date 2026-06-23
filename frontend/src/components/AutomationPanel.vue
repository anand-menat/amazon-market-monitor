<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Play, Plus, Trash2 } from 'lucide-vue-next'
import { api } from '../services/api'

const jobs = ref([])
const runs = ref([])
const loading = ref(false)
const error = ref('')
const form = reactive({
  name: '',
  asin: '',
  domain: 'com',
  country_code: 'us',
  with_competitors: true,
  pages: 2,
  interval_minutes: null,
  enabled: true
})

const loadJobs = async () => {
  error.value = ''
  try {
    const data = await api.getJobs()
    jobs.value = data.jobs
    runs.value = data.recent_runs
  } catch (err) {
    error.value = err.message
  }
}

const createJob = async () => {
  if (!form.name || !form.asin) return
  loading.value = true
  error.value = ''
  try {
    const payload = {
      ...form,
      interval_minutes: form.interval_minutes ? Number(form.interval_minutes) : null,
      pages: Number(form.pages)
    }
    await api.createJob(payload)
    form.name = ''
    form.asin = ''
    await loadJobs()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const runJob = async (jobId) => {
  loading.value = true
  error.value = ''
  try {
    await api.runJob(jobId)
    await loadJobs()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const deleteJob = async (jobId) => {
  await api.deleteJob(jobId)
  await loadJobs()
}

onMounted(loadJobs)
</script>

<template>
  <section class="panel automation-panel">
    <div>
      <p class="panel-kicker">Automation</p>
      <h2>Scrape jobs</h2>
    </div>

    <div v-if="error" class="notice error">{{ error }}</div>

    <form class="job-form" @submit.prevent="createJob">
      <input v-model="form.name" placeholder="Daily monitor" />
      <input v-model="form.asin" placeholder="ASIN" />
      <div class="field-grid">
        <select v-model="form.domain">
          <option value="com">com</option>
          <option value="co.uk">co.uk</option>
          <option value="de">de</option>
          <option value="in">in</option>
        </select>
        <select v-model="form.country_code">
          <option value="us">us</option>
          <option value="gb">gb</option>
          <option value="de">de</option>
          <option value="in">in</option>
        </select>
      </div>
      <input v-model="form.interval_minutes" type="number" min="15" placeholder="Interval minutes" />
      <label class="checkbox-row">
        <input v-model="form.with_competitors" type="checkbox" />
        <span>Include competitors</span>
      </label>
      <button class="primary-button" :disabled="loading || !form.name || !form.asin">
        <Plus :size="17" />
        Create job
      </button>
    </form>

    <div class="job-list">
      <article v-for="job in jobs" :key="job.id" class="job-item">
        <div>
          <strong>{{ job.name }}</strong>
          <span>{{ job.asin }} | every {{ job.interval_minutes || 'manual' }} min</span>
        </div>
        <div class="icon-actions">
          <button :title="`Run ${job.name}`" @click="runJob(job.id)">
            <Play :size="16" />
          </button>
          <button :title="`Delete ${job.name}`" @click="deleteJob(job.id)">
            <Trash2 :size="16" />
          </button>
        </div>
      </article>
    </div>

    <div v-if="runs.length" class="run-list">
      <p class="panel-kicker">Recent runs</p>
      <span v-for="run in runs.slice(0, 4)" :key="run.id" :class="['run-pill', run.status]">
        {{ run.status }} | {{ run.competitors_found }} comps
      </span>
    </div>
  </section>
</template>
