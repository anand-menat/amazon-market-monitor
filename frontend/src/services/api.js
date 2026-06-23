const request = async (path, options = {}) => {
  const apiKey = localStorage.getItem('api_key')
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  }
  
  if (apiKey) {
    headers['X-API-Key'] = apiKey
  }

  const response = await fetch(path, {
    headers,
    ...options
  })

  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(payload.detail || 'Request failed')
  }
  return payload
}

export const api = {
  scrapeProduct: (payload) =>
    request('/api/products/scrape', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),

  runProductWorkflow: (payload) =>
    request('/api/products/workflow', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),

  getProducts: (page = 1, perPage = 10) =>
    request(`/api/products?page=${page}&per_page=${perPage}`),

  deleteProduct: (asin) =>
    request(`/api/products/${asin}`, {
      method: 'DELETE'
    }),

  clearAllProducts: () =>
    request('/api/products', {
      method: 'DELETE'
    }),

  fetchCompetitors: (asin, payload) =>
    request(`/api/products/${asin}/competitors`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),

  getCompetitors: (asin) => request(`/api/products/${asin}/competitors`),

  getPriceHistory: (asin, limit = 20) =>
    request(`/api/products/${asin}/price-history?limit=${limit}`),

  analyzeProduct: (asin) =>
    request(`/api/products/${asin}/analyze`, {
      method: 'POST'
    }),

  getJobs: () => request('/api/jobs'),

  createJob: (payload) =>
    request('/api/jobs', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),

  runJob: (jobId) =>
    request(`/api/jobs/${jobId}/run`, {
      method: 'POST'
    }),

  deleteJob: (jobId) =>
    request(`/api/jobs/${jobId}`, {
      method: 'DELETE'
    })
}
