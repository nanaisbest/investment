import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// ===== 综合接口 =====
export const getOverview = () => api.get('/overview')
export const getRealtime = (codes) => api.get('/realtime', { params: { codes } })
export const getAllStocks = (page = 1, size = 50, sort_by = 'code', order = 'asc') =>
  api.get('/stocks/all', { params: { page, size, sort_by, order } })

// ===== mootdx 接口 =====
export const mootdxQuote = (codes) => api.get('/mootdx/quote', { params: { codes } })
export const mootdxKline = (symbol, period = 9, count = 100) =>
  api.get('/mootdx/kline', { params: { symbol, period, count } })
export const mootdxStockList = (market = 0) =>
  api.get('/mootdx/stock-list', { params: { market } })

// ===== 腾讯财经接口 =====
export const tencentQuote = (codes) => api.get('/tencent/quote', { params: { codes } })
export const tencentIndicators = (codes) => api.get('/tencent/indicators', { params: { codes } })
export const tencentKline = (symbol, period = 4, count = 100) =>
  api.get('/tencent/kline', { params: { symbol, period, count } })

// ===== akshare 接口 =====
export const akshareNews = (symbol = '') => api.get('/akshare/news', { params: { symbol } })
export const akshareResearch = (symbol) => api.get('/akshare/research', { params: { symbol } })
export const akshareSentiment = () => api.get('/akshare/sentiment')

// ===== 同花顺问财接口 =====
export const iwencaiSearch = (q) => api.get('/iwencai/search', { params: { q } })

// ===== 同花顺热点接口 =====
export const tonghuashunHotConcepts = () => api.get('/tonghuashun/hot-concepts')
export const tonghuashunStrongStocks = () => api.get('/tonghuashun/strong-stocks')
export const tonghuashunAttribution = (code) =>
  api.get('/tonghuashun/attribution', { params: { code } })

// ===== 巨潮资讯网接口 =====
export const cninfoAnnouncements = (params) => api.get('/cninfo/announcements', { params })
export const cninfoStockList = () => api.get('/cninfo/stock-list')
export const cninfoDailyQuotes = (code) => api.get('/cninfo/daily-quotes', { params: { code } })

// ===== AI 分析接口 =====
export const analyzeBuffettOracle = (stock_code) =>
  api.get('/analysis/buffett-oracle', { params: { stock_code }, timeout: 60000 })
export const chatWithBuffettOracle = (sessionId, message, stockCode) =>
  api.post('/analysis/buffett-oracle/chat', { session_id: sessionId, message, stock_code: stockCode }, { timeout: 120000 })
