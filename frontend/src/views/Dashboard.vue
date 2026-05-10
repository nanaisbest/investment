<template>
  <div class="dashboard">
    <!-- 顶部导航 -->
    <header class="header">
      <div class="header-left">
        <div class="logo">
          <span class="logo-icon">◆</span>
          <h1 class="logo-text">投资数据<span>平台</span></h1>
        </div>
        <span class="header-tagline">五大数据源 · 一站式接入</span>
      </div>
      <div class="header-right">
        <el-tag :type="backendOnline ? 'danger' : 'info'" effect="dark" round>
          {{ backendOnline ? '● 服务在线' : '○ 服务离线' }}
        </el-tag>
        <el-button circle :icon="Refresh" @click="refreshAll" :loading="refreshing" />
      </div>
    </header>

    <!-- 主体内容 -->
    <main class="main-content">
      <!-- 指数概览卡片 -->
      <section class="index-cards">
        <div
          v-for="idx in indices"
          :key="idx.code"
          class="premium-card index-card"
        >
          <div class="stat-label">{{ idx.name }}</div>
          <div class="stat-number" :class="idx.change >= 0 ? 'stat-up' : 'stat-down'">
            {{ idx.price?.toFixed(2) || '--' }}
          </div>
          <div class="index-change" :class="idx.change >= 0 ? 'stat-up' : 'stat-down'">
            <span>{{ idx.change >= 0 ? '▲' : '▼' }}</span>
            <span>{{ Math.abs(idx.change).toFixed(2) }}%</span>
          </div>
          <div class="index-volume">成交 {{ formatVolume(idx.volume) }}</div>
        </div>
      </section>

      <!-- 数据源标签页 -->
      <el-card class="datasource-panel">
        <el-tabs v-model="activeTab" type="border-card">
          <!-- 腾讯财经 - 实时行情 -->
          <el-tab-pane name="tencent">
            <template #label>
              <span class="tab-label">
                <span class="source-tag tencent">腾讯财经</span> 实时行情
              </span>
            </template>
            <div class="tab-toolbar">
              <el-input
                v-model="quoteCodes"
                placeholder="输入股票代码（如 000001），留空查全部"
                style="width: 360px"
                clearable
                @keyup.enter="fetchTencentQuote"
                @clear="fetchTencentQuote"
              />
              <el-button type="primary" @click="fetchTencentQuote" :loading="tencentLoading">
                查询行情
              </el-button>
            </div>
            <el-table :data="tencentData" stripe max-height="400" v-loading="tencentLoading"
              highlight-current-row @row-click="jumpToKline"
              @sort-change="onSortChange"
              :default-sort="{ prop: 'code', order: 'ascending' }"
            >
              <el-table-column prop="name" label="名称" width="120" sortable="custom" />
              <el-table-column prop="code" label="代码" width="100" sortable="custom" />
              <el-table-column prop="current" label="现价" sortable="custom">
                <template #default="{ row }">{{ row.current?.toFixed(2) }}</template>
              </el-table-column>
              <el-table-column prop="change_pct" label="涨跌幅" sortable="custom">
                <template #default="{ row }">
                  <span :class="row.change_pct >= 0 ? 'stat-up' : 'stat-down'">
                    {{ row.change_pct?.toFixed(2) }}%
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="open" label="今开" width="80" />
              <el-table-column prop="high" label="最高" width="80" />
              <el-table-column prop="low" label="最低" width="80" />
              <el-table-column prop="volume" label="成交量" width="100" sortable="custom">
                <template #default="{ row }">{{ formatVolume(row.volume) }}</template>
              </el-table-column>
              <el-table-column prop="turnover" label="换手率" width="80" sortable="custom" />
              <el-table-column prop="pe" label="市盈率" width="80" sortable="custom" />
            </el-table>
            <div v-if="isAllMode" class="pagination-bar">
              <el-button size="small" :disabled="allStockPage <= 1" @click="goPage(1)">首页</el-button>
              <el-button size="small" :disabled="allStockPage <= 1" @click="goPage(allStockPage - 1)">上一页</el-button>
              <span class="page-jump">
                第 <el-input v-model="jumpPage" size="small" style="width:60px" @keyup.enter="doJumpPage" /> 页
                <el-button size="small" @click="doJumpPage">跳转</el-button>
              </span>
              <el-button size="small" :disabled="allStockPage >= allStockTotalPages" @click="goPage(allStockPage + 1)">下一页</el-button>
              <el-button size="small" :disabled="allStockPage >= allStockTotalPages" @click="goPage(allStockTotalPages)">末页</el-button>
              <span class="page-info">共 {{ allStockTotal }} 只 ｜ {{ allStockPage }} / {{ allStockTotalPages }} 页</span>
            </div>
          </el-tab-pane>

          <!-- mootdx - K线及盘口 -->
          <el-tab-pane name="mootdx">
            <template #label>
              <span class="tab-label">
                <span class="source-tag mootdx">mootdx</span> K线数据
              </span>
            </template>
            <div class="tab-toolbar">
              <el-input
                v-model="mootdxSymbol"
                placeholder="股票代码"
                style="width: 160px"
                clearable
              />
              <el-select v-model="mootdxPeriod" style="width: 140px">
                <el-option label="日线" :value="0" />
                <el-option label="周线" :value="1" />
                <el-option label="月线" :value="2" />
                <el-option label="5分钟" :value="5" />
                <el-option label="15分钟" :value="6" />
                <el-option label="30分钟" :value="7" />
                <el-option label="60分钟" :value="8" />
                <el-option label="1分钟" :value="9" />
              </el-select>
              <el-button type="primary" @click="fetchMootdxKline" :loading="mootdxLoading">
                获取K线
              </el-button>
            </div>
            <div ref="klineChart" class="chart-container"></div>
          </el-tab-pane>

          <!-- akshare - 市场情绪 -->
          <el-tab-pane name="akshare">
            <template #label>
              <span class="tab-label">
                <span class="source-tag akshare">akshare</span> 市场情绪
              </span>
            </template>
            <div class="tab-toolbar">
              <el-button type="primary" @click="fetchAkshareSentiment" :loading="akshareLoading">
                涨停板数据
              </el-button>
              <el-button @click="fetchAkshareNews" :loading="akshareNewsLoading">
                市场要闻
              </el-button>
            </div>
            <!-- 涨停板表格 -->
            <el-table v-if="akshareSentimentData.length > 0" :data="akshareSentimentData" stripe max-height="400" v-loading="akshareLoading" style="margin-bottom: 16px">
              <el-table-column prop="名称" label="名称" width="120" />
              <el-table-column prop="代码" label="代码" width="100" />
              <el-table-column prop="涨跌幅" label="涨跌幅" sortable />
              <el-table-column prop="涨停时间" label="涨停时间" width="120" />
              <el-table-column prop="封单资金" label="封单资金" width="120" />
              <el-table-column prop="换手率" label="换手率" />
              <el-table-column prop="成交额" label="成交额" />
            </el-table>
            <el-empty v-else-if="!akshareLoading && !akshareNewsLoading && akshareNewsData.length === 0" description="点击按钮获取数据" />
            <!-- 新闻表格 -->
            <el-table v-if="akshareNewsData.length > 0" :data="akshareNewsData" stripe max-height="400" v-loading="akshareNewsLoading">
              <el-table-column prop="新闻标题" label="新闻标题" min-width="280">
                <template #default="{ row }">
                  <a :href="row['新闻链接']" target="_blank" class="news-link">{{ row['新闻标题'] }}</a>
                </template>
              </el-table-column>
              <el-table-column prop="发布时间" label="发布时间" width="160" />
              <el-table-column prop="文章来源" label="来源" width="140" />
              <el-table-column prop="关键词" label="关键词" width="100" />
            </el-table>
          </el-tab-pane>

          <!-- 同花顺热点 -->
          <el-tab-pane name="tonghuashun">
            <template #label>
              <span class="tab-label">
                <span class="source-tag tonghuashun">同花顺热点</span> 热点追踪
              </span>
            </template>
            <div class="tab-toolbar">
              <el-button type="primary" @click="fetchHotConcepts" :loading="thsLoading">
                热门概念
              </el-button>
              <el-button type="primary" @click="fetchStrongStocks" :loading="thsStrongLoading">
                强势股
              </el-button>
            </div>
            <el-row :gutter="20">
              <el-col :span="12">
                <h4 class="section-subtitle">热门概念板块</h4>
                <el-table :data="hotConcepts" stripe max-height="400" v-loading="thsLoading">
                  <el-table-column prop="name" label="概念名称" />
                  <el-table-column prop="change_pct" label="涨幅%" sortable />
                  <el-table-column prop="leading_stock" label="龙头股" />
                  <el-table-column prop="stock_count" label="成分股数" />
                </el-table>
              </el-col>
              <el-col :span="12">
                <h4 class="section-subtitle">强势股排行</h4>
                <el-table :data="strongStocks" stripe max-height="400" v-loading="thsStrongLoading">
                  <el-table-column prop="name" label="名称" width="100" />
                  <el-table-column prop="code" label="代码" width="80" />
                  <el-table-column prop="price" label="现价" />
                  <el-table-column prop="change_pct" label="涨跌幅%" sortable>
                    <template #default="{ row }">
                      <span :class="(row.change_pct || 0) >= 0 ? 'stat-up' : 'stat-down'">
                        {{ row.change_pct }}%
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="turnover" label="换手率%" />
                </el-table>
              </el-col>
            </el-row>
          </el-tab-pane>

          <!-- 同花顺问财 - 语义搜索 -->
          <el-tab-pane name="iwencai">
            <template #label>
              <span class="tab-label">
                <span class="source-tag iwencai">问财</span> 语义搜索
              </span>
            </template>
            <div class="tab-toolbar">
              <el-input
                v-model="iwencaiQuery"
                placeholder="输入条件：涨停 | 跌停 | 次新股 | 连续上涨"
                style="width: 480px"
                clearable
                @keyup.enter="fetchIwencai"
              />
              <el-button type="primary" @click="fetchIwencai" :loading="iwencaiLoading">
                搜索
              </el-button>
            </div>
            <el-table :data="iwencaiResult" stripe max-height="400" v-loading="iwencaiLoading">
              <el-table-column prop="code" label="代码" width="100" />
              <el-table-column prop="name" label="名称" width="120" />
              <el-table-column prop="price" label="现价" />
              <el-table-column prop="change_pct" label="涨跌幅">
                <template #default="{ row }">
                  <span :class="(row.change_pct || 0) >= 0 ? 'stat-up' : 'stat-down'">
                    {{ row.change_pct }}%
                  </span>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <!-- 底部数据源状态 -->
      <section class="source-status">
        <div
          v-for="src in dataSources"
          :key="src.name"
          class="premium-card source-status-card"
          :class="{ active: activeTab === src.tab }"
          @click="activeTab = src.tab"
        >
          <div class="source-status-header">
            <span :class="`source-tag ${src.tag}`">{{ src.name }}</span>
            <el-icon :size="12" color="var(--accent)"><Right /></el-icon>
          </div>
          <div class="source-desc">{{ src.desc }}</div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, nextTick } from 'vue'
import { Refresh, Right } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  getOverview,
  tencentQuote,
  getAllStocks,
  mootdxKline,
  akshareSentiment,
  akshareNews,
  tonghuashunHotConcepts,
  tonghuashunStrongStocks,
  iwencaiSearch,
} from '../api'

// ===== 状态 =====
const backendOnline = ref(false)
const refreshing = ref(false)
const activeTab = ref('tencent')

// 指数数据
const indices = reactive([
  { code: 'sh000001', name: '上证指数', price: 0, change: 0, volume: 0 },
  { code: 'sz399001', name: '深证成指', price: 0, change: 0, volume: 0 },
  { code: 'sz399006', name: '创业板指', price: 0, change: 0, volume: 0 },
  { code: 'sh000688', name: '科创50', price: 0, change: 0, volume: 0 },
])

// 腾讯财经
const quoteCodes = ref('')
const tencentData = ref([])
const tencentLoading = ref(false)
const allStockPage = ref(1)
const allStockTotal = ref(0)
const allStockTotalPages = ref(0)
const isAllMode = ref(false)
const jumpPage = ref('')
const sortBy = ref('code')
const sortOrder = ref('asc')

// mootdx
const mootdxSymbol = ref('000001')
const mootdxPeriod = ref(0)
const mootdxLoading = ref(false)
const klineChart = ref(null)
let klineChartInstance = null

// akshare
const akshareSentimentData = ref([])
const akshareLoading = ref(false)
const akshareNewsData = ref([])
const akshareNewsLoading = ref(false)

// 同花顺热点
const hotConcepts = ref([])
const strongStocks = ref([])
const thsLoading = ref(false)
const thsStrongLoading = ref(false)

// 问财
const iwencaiQuery = ref('涨停')
const iwencaiResult = ref([])
const iwencaiLoading = ref(false)

// 数据源列表
const dataSources = [
  { name: '腾讯财经', tag: 'tencent', tab: 'tencent', desc: '实时行情 · 秒级响应 · 免费无需认证' },
  { name: 'mootdx', tag: 'mootdx', tab: 'mootdx', desc: 'K线数据 · 实时盘口 · 通达信协议' },
  { name: 'akshare', tag: 'akshare', tab: 'akshare', desc: '市场情绪 · 研报新闻 · 数据广泛' },
  { name: '同花顺热点', tag: 'tonghuashun', tab: 'tonghuashun', desc: '热点追踪 · 题材归因 · 短线利器' },
  { name: '问财', tag: 'iwencai', tab: 'iwencai', desc: '自然语言 · 语义搜索 · 智能选股' },
]

// ===== 方法 =====
function formatVolume(vol) {
  if (!vol) return '--'
  if (vol >= 1e8) return (vol / 1e8).toFixed(2) + '亿'
  if (vol >= 1e4) return (vol / 1e4).toFixed(2) + '万'
  return vol.toFixed(0)
}

async function fetchOverview() {
  try {
    const { data } = await getOverview()
    if (data.status === 'success' && data.data) {
      backendOnline.value = true
      data.data.forEach((item) => {
        const idx = indices.find((i) => i.code.replace('sh', '').replace('sz', '') === item.code)
        if (idx) {
          idx.price = item.current
          idx.change = item.change_pct
          idx.volume = item.volume
        }
      })
    }
  } catch {
    backendOnline.value = false
  }
}

const DEFAULT_STOCKS = '000001,600519,000858,300750,601318,002415,600036,601166,000002,002594,600030,601988,000651,603259,600276'

async function fetchTencentQuote() {
  tencentLoading.value = true
  try {
    if (quoteCodes.value.trim()) {
      isAllMode.value = false
      const { data } = await tencentQuote(quoteCodes.value)
      if (data.status === 'success') tencentData.value = data.data || []
    } else {
      isAllMode.value = true
      await loadAllStocksPage(allStockPage.value)
    }
  } finally {
    tencentLoading.value = false
  }
}

async function loadAllStocksPage(p) {
  const { data } = await getAllStocks(p, 50, sortBy.value, sortOrder.value)
  if (data.status === 'success') {
    tencentData.value = data.data || []
    allStockTotal.value = data.total || 0
    allStockTotalPages.value = data.total_pages || 0
  }
}

async function goPage(p) {
  allStockPage.value = p
  tencentLoading.value = true
  try {
    await loadAllStocksPage(p)
  } finally {
    tencentLoading.value = false
  }
}

function doJumpPage() {
  const p = parseInt(jumpPage.value)
  if (p >= 1 && p <= allStockTotalPages.value) {
    goPage(p)
  }
  jumpPage.value = ''
}

function onSortChange({ prop, order }) {
  if (!prop || !isAllMode.value) return
  sortBy.value = prop
  sortOrder.value = order === 'ascending' ? 'asc' : order === 'descending' ? 'desc' : 'asc'
  goPage(1)
}

function jumpToKline(row) {
  if (!row || !row.code) return
  mootdxSymbol.value = row.code
  activeTab.value = 'mootdx'
  nextTick(() => fetchMootdxKline())
}

async function fetchMootdxKline() {
  mootdxLoading.value = true
  try {
    const { data } = await mootdxKline(mootdxSymbol.value, mootdxPeriod.value, 100)
    if (data.status === 'success' && data.data) {
      await nextTick()
      renderKlineChart(data.data)
    }
  } finally {
    mootdxLoading.value = false
  }
}

function renderKlineChart(rawData) {
  if (!klineChart.value) return
  if (!klineChartInstance) {
    klineChartInstance = echarts.init(klineChart.value, 'dark')
  }

  if (!rawData || rawData.length === 0) {
    klineChartInstance.setOption({
      title: { text: '暂无K线数据', left: 'center', top: 'center', textStyle: { color: '#666', fontSize: 16 } }
    }, true)
    return
  }

  const reversed = [...rawData].reverse()
  const dates = reversed.map((d) => d.date || d.datetime || d.time || '')
  const prices = reversed.map((d) => d.close || 0)
  const volumes = reversed.map((d) => d.volume || d.vol || 0)

  const option = {
    backgroundColor: 'transparent',
    grid: [
      { left: '4%', right: '4%', top: '5%', height: '55%' },
      { left: '4%', right: '4%', top: '70%', height: '20%' },
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: '#333' } },
        axisLabel: { color: '#888', fontSize: 10 },
        gridIndex: 0,
      },
      {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: '#333' } },
        axisLabel: { show: false },
        gridIndex: 1,
      },
    ],
    yAxis: [
      {
        type: 'value',
        scale: true,
        axisLine: { lineStyle: { color: '#333' } },
        axisLabel: { color: '#888' },
        splitLine: { lineStyle: { color: '#1a1a1a' } },
        gridIndex: 0,
      },
      {
        type: 'value',
        axisLine: { lineStyle: { color: '#333' } },
        axisLabel: { show: false },
        splitLine: { show: false },
        gridIndex: 1,
      },
    ],
    series: [
      {
        name: '收盘价',
        type: 'line',
        data: prices,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#e63946', width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(230,57,70,0.3)' },
            { offset: 1, color: 'rgba(230,57,70,0.02)' },
          ]),
        },
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
      {
        name: '成交量',
        type: 'bar',
        data: volumes,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(230,57,70,0.4)' },
            { offset: 1, color: 'rgba(230,57,70,0.05)' },
          ]),
        },
        xAxisIndex: 1,
        yAxisIndex: 1,
      },
    ],
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(26,26,26,0.95)',
      borderColor: '#333',
      textStyle: { color: '#e8e8e8', fontSize: 12 },
    },
  }

  klineChartInstance.setOption(option, true)
}

async function fetchAkshareSentiment() {
  akshareLoading.value = true
  try {
    const { data } = await akshareSentiment()
    if (data.status === 'success') akshareSentimentData.value = data.data || []
  } finally {
    akshareLoading.value = false
  }
}

async function fetchAkshareNews() {
  akshareNewsLoading.value = true
  try {
    const { data } = await akshareNews()
    if (data.status === 'success') {
      akshareNewsData.value = data.data || []
    }
  } finally {
    akshareNewsLoading.value = false
  }
}

async function fetchHotConcepts() {
  thsLoading.value = true
  try {
    const { data } = await tonghuashunHotConcepts()
    if (data.status === 'success') hotConcepts.value = data.data || []
  } finally {
    thsLoading.value = false
  }
}

async function fetchStrongStocks() {
  thsStrongLoading.value = true
  try {
    const { data } = await tonghuashunStrongStocks()
    if (data.status === 'success') strongStocks.value = data.data || []
  } finally {
    thsStrongLoading.value = false
  }
}

async function fetchIwencai() {
  iwencaiLoading.value = true
  try {
    const { data } = await iwencaiSearch(iwencaiQuery.value)
    if (data.status === 'success') iwencaiResult.value = data.data || []
  } finally {
    iwencaiLoading.value = false
  }
}

async function refreshAll() {
  refreshing.value = true
  await fetchOverview()
  await fetchTencentQuote()
  refreshing.value = false
}

// ===== 生命周期 =====
onMounted(() => {
  fetchOverview()
  fetchTencentQuote()
})

// 窗口大小变化时重绘图表
window.addEventListener('resize', () => {
  klineChartInstance?.resize()
})
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: var(--bg-primary);
}

/* 顶部导航 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow-lg);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  font-size: 1.8rem;
  color: var(--accent);
  filter: drop-shadow(0 0 8px var(--accent-glow));
}

.logo-text {
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: 2px;
}
.logo-text span {
  color: var(--accent);
}

.header-tagline {
  color: var(--text-muted);
  font-size: 0.85rem;
  letter-spacing: 1px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 主体 */
.main-content {
  padding: 24px 32px;
  max-width: 1600px;
  margin: 0 auto;
}

/* 指数卡片 */
.index-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.index-card {
  text-align: center;
  cursor: pointer;
}

.index-change {
  margin-top: 6px;
  font-size: 0.95rem;
  font-weight: 600;
}

.index-volume {
  margin-top: 8px;
  font-size: 0.78rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

/* 数据源面板 */
.datasource-panel {
  margin-bottom: 24px;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tab-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}

.chart-container {
  width: 100%;
  height: 420px;
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}

.section-subtitle {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 12px;
  padding-left: 4px;
}

/* 底部数据源状态 */
.source-status {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 40px;
}

.source-status-card {
  cursor: pointer;
  padding: 16px;
  text-align: center;
  border: 1px solid var(--border);
  transition: all 0.3s ease;
}

.source-status-card.active {
  border-color: var(--accent);
  box-shadow: var(--shadow-red);
}

.source-status-card:hover {
  border-color: var(--accent);
  box-shadow: var(--shadow-red);
}

.source-status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.source-desc {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-align: left;
  line-height: 1.4;
}

/* 新闻链接 */
:deep(.news-link) {
  color: #60a5fa;
  text-decoration: none;
  transition: color 0.2s;
}
:deep(.news-link:hover) {
  color: var(--accent-light);
}

/* 分页栏 */
.pagination-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding: 12px 0;
}
.page-info {
  color: var(--text-secondary);
  font-size: 0.85rem;
}

/* 响应式 */
@media (max-width: 1200px) {
  .index-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  .source-status {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .index-cards {
    grid-template-columns: 1fr;
  }
  .source-status {
    grid-template-columns: 1fr;
  }
  .main-content {
    padding: 16px;
  }
}
</style>
