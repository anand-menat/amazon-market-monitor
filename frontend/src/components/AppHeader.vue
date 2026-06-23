<script setup>
import { Bot, Gauge, Workflow } from 'lucide-vue-next'
</script>

<template>
  <header class="app-header">
    <div class="logo-area">
      <p class="eyebrow">Competitor Analysis</p>
      <h1>Amazon Dashboard</h1>
    </div>
    <div class="header-metrics">
      <span><Bot :size="16" /> Python scraping</span>
      <span><Workflow :size="16" /> Scheduled jobs</span>
      <span><Gauge :size="16" /> FastAPI monitor</span>
    </div>
  </header>
</template>
