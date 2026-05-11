<template>
  <div class="dashboard">
    <!-- 顶部导航 -->
    <header class="header">
      <div class="header-left">
        <div class="logo">
          <span class="logo-icon">◆</span>
          <h1 class="logo-text">投资数据<span>平台</span></h1>
        </div>
        <span class="header-tagline">七大数据源 · 一站式接入</span>
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
                <el-option label="1分钟" :value="8" />
                <el-option label="5分钟" :value="0" />
                <el-option label="15分钟" :value="1" />
                <el-option label="30分钟" :value="2" />
                <el-option label="60分钟" :value="3" />
                <el-option label="日线" :value="4" />
                <el-option label="周线" :value="5" />
                <el-option label="月线" :value="6" />
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

          <!-- 巨潮资讯网 - 公告查询 -->
          <el-tab-pane name="cninfo">
            <template #label>
              <span class="tab-label">
                <span class="source-tag cninfo">巨潮资讯</span> 公告查询
              </span>
            </template>
            <div class="tab-toolbar">
              <el-input
                v-model="cninfoStockCode"
                placeholder="股票代码，如 000001"
                style="width: 180px"
                clearable
                @keyup.enter="onCninfoSearch"
              />
              <el-select v-model="cninfoCategory" style="width: 140px" placeholder="公告类别" @change="onCninfoSearch">
                <el-option
                  v-for="cat in cninfoCategories"
                  :key="cat.value"
                  :label="cat.label"
                  :value="cat.value"
                />
              </el-select>
              <el-input
                v-model="cninfoKeyword"
                placeholder="关键词搜索（如 分红、重组）"
                style="width: 240px"
                clearable
                @keyup.enter="onCninfoSearch"
              />
              <el-button type="primary" @click="onCninfoSearch" :loading="cninfoLoading">
                查询公告
              </el-button>
            </div>
            <div class="tab-toolbar">
              <el-date-picker
                v-model="cninfoStartDate"
                type="date"
                placeholder="开始日期"
                style="width: 160px"
                value-format="YYYY-MM-DD"
              />
              <span style="color: var(--text-muted); line-height: 32px; margin: 0 8px;">至</span>
              <el-date-picker
                v-model="cninfoEndDate"
                type="date"
                placeholder="结束日期"
                style="width: 160px"
                value-format="YYYY-MM-DD"
              />
              <el-button @click="cninfoStartDate = ''; cninfoEndDate = ''; onCninfoSearch()">清除日期</el-button>
            </div>
            <el-table :data="cninfoData" stripe max-height="450" v-loading="cninfoLoading">
              <el-table-column prop="code" label="股票代码" width="100" />
              <el-table-column prop="name" label="股票名称" width="120" />
              <el-table-column prop="title" label="公告标题" min-width="300">
                <template #default="{ row }">
                  <a
                    v-if="row.pdf_url"
                    :href="row.pdf_url"
                    target="_blank"
                    class="news-link"
                    @click.prevent="openPdf(row.pdf_url)"
                  >
                    {{ row.title }}
                  </a>
                  <span v-else>{{ row.title }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="time" label="公告时间" width="170">
                <template #default="{ row }">
                  {{ formatTimestamp(row.time) }}
                </template>
              </el-table-column>
              <el-table-column prop="pdf_type" label="类型" width="80" />
            </el-table>
            <div v-if="cninfoTotal > cninfoPageSize" class="pagination-bar">
              <el-button size="small" :disabled="cninfoPage <= 1" @click="cninfoGoPage(1)">首页</el-button>
              <el-button size="small" :disabled="cninfoPage <= 1" @click="cninfoGoPage(cninfoPage - 1)">上一页</el-button>
              <span class="page-info">第 {{ cninfoPage }} 页 / 共 {{ Math.ceil(cninfoTotal / cninfoPageSize) }} 页（{{ cninfoTotal }} 条）</span>
              <el-button size="small" :disabled="cninfoPage >= Math.ceil(cninfoTotal / cninfoPageSize)" @click="cninfoGoPage(cninfoPage + 1)">下一页</el-button>
              <el-button size="small" :disabled="cninfoPage >= Math.ceil(cninfoTotal / cninfoPageSize)" @click="cninfoGoPage(Math.ceil(cninfoTotal / cninfoPageSize))">末页</el-button>
            </div>
            <el-empty v-if="!cninfoLoading && cninfoData.length === 0" description="输入股票代码查询公告，如 000001 或 600519" />
          </el-tab-pane>

          <!-- 巴菲特先知 - AI 交互式对话 -->
          <el-tab-pane name="buffett">
            <template #label>
              <span class="tab-label">
                <span class="source-tag buffett">巴菲特先知</span> AI 对话
              </span>
            </template>
            <div class="chat-container">
              <!-- 消息列表 -->
              <div class="chat-messages" ref="chatMessagesRef">
                <div v-if="buffettMessages.length === 0 && !buffettLoading" class="chat-welcome">
                  <div class="welcome-icon">📊</div>
                  <p class="welcome-title">巴菲特先知 · 价值投资对话</p>
                  <p class="welcome-sub">你可以直接提问，或输入股票代码进行深度分析</p>
                  <div class="quick-actions">
                    <el-tag v-for="q in quickQuestions" :key="q" class="quick-tag" @click="sendMessage(q)" type="info">
                      {{ q }}
                    </el-tag>
                  </div>
                </div>
                <div v-for="(msg, idx) in buffettMessages" :key="idx" class="chat-bubble-row" :class="msg.role === 'user' ? 'chat-row-user' : 'chat-row-ai'">
                  <div class="chat-bubble" :class="msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'">
                    <div v-if="msg.role === 'assistant'" class="bubble-content" v-html="msg.rendered" />
                    <div v-else class="bubble-content">{{ msg.content }}</div>
                    <div v-if="msg.score" class="bubble-score">
                      <el-tag :type="msg.score >= 7 ? 'success' : msg.score >= 5 ? 'warning' : 'danger'" size="small">
                        综合评分: {{ msg.score }}/10
                      </el-tag>
                    </div>
                  </div>
                </div>
                <div v-if="buffettLoading" class="chat-bubble-row chat-row-ai">
                  <div class="chat-bubble chat-bubble-ai">
                    <div class="typing-indicator"><span></span><span></span><span></span></div>
                  </div>
                </div>
              </div>
              <!-- 输入区 -->
              <div class="chat-input-area">
                <div v-if="buffettStockCode" class="chat-stock-tag">
                  <el-tag closable @close="clearStockCode" type="warning" size="small">
                    分析中: {{ buffettStockCode }}
                  </el-tag>
                </div>
                <div class="chat-input-row">
                  <el-input
                    v-model="buffettInput"
                    placeholder="输入股票代码或问题，如 000001 或 分析 600519..."
                    size="default"
                    clearable
                    @keyup.enter="sendMessage()"
                    class="chat-input-main"
                  />
                  <el-button type="primary" @click="sendMessage()" :loading="buffettLoading" :disabled="!buffettInput.trim()">
                    发送
                  </el-button>
                </div>
              </div>
            </div>
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
import { ref, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { Refresh, Right } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  getOverview,
  tencentQuote,
  getAllStocks,
  tencentKline,
  akshareSentiment,
  akshareNews,
  tonghuashunHotConcepts,
  tonghuashunStrongStocks,
  iwencaiSearch,
  cninfoAnnouncements,
  analyzeBuffettOracle,
  chatWithBuffettOracle,
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
const mootdxPeriod = ref(4)
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

// 巨潮资讯网
const cninfoStockCode = ref('')
const cninfoKeyword = ref('')
const cninfoCategory = ref('')
const cninfoStartDate = ref('')
const cninfoEndDate = ref('')
const cninfoData = ref([])
const cninfoLoading = ref(false)
const cninfoTotal = ref(0)
const cninfoPage = ref(1)
const cninfoPageSize = ref(30)
const cninfoCategories = [
  { label: '全部公告', value: '' },
  { label: '年度报告', value: 'category_ndbg_szsh' },
  { label: '半年度报告', value: 'category_bndbg_szsh' },
  { label: '一季度报告', value: 'category_yjdbg_szsh' },
  { label: '三季度报告', value: 'category_sjdbg_szsh' },
]

// 巴菲特先知 - 对话
const buffettInput = ref('')
const buffettStockCode = ref('')
const buffettMessages = ref([])
const buffettLoading = ref(false)
const chatMessagesRef = ref(null)
const buffettSessionId = ref('')
const quickQuestions = [
  '分析 000001 平安银行',
  '分析 600519 贵州茅台',
  '对比银行股和白酒股的投资价值',
  '什么是DCF估值法？怎么用？',
  '如何判断一家公司有护城河？',
  '市盈率5倍意味着什么？',
]

// 数据源列表
const dataSources = [
  { name: '腾讯财经', tag: 'tencent', tab: 'tencent', desc: '实时行情 · 秒级响应 · 免费无需认证' },
  { name: 'mootdx', tag: 'mootdx', tab: 'mootdx', desc: 'K线数据 · 实时盘口 · 通达信协议' },
  { name: 'akshare', tag: 'akshare', tab: 'akshare', desc: '市场情绪 · 研报新闻 · 数据广泛' },
  { name: '同花顺热点', tag: 'tonghuashun', tab: 'tonghuashun', desc: '热点追踪 · 题材归因 · 短线利器' },
  { name: '问财', tag: 'iwencai', tab: 'iwencai', desc: '自然语言 · 语义搜索 · 智能选股' },
  { name: '巨潮资讯', tag: 'cninfo', tab: 'cninfo', desc: '官方公告 · 年报季报 · PDF原文' },
  { name: '巴菲特先知', tag: 'buffett', tab: 'buffett', desc: 'AI价值投资 · 全维度分析 · 巴菲特框架' },
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
    const { data } = await tencentKline(mootdxSymbol.value, mootdxPeriod.value, 100)
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

  klineChartInstance.clear()

  if (!rawData || rawData.length === 0) {
    klineChartInstance.setOption({
      title: { text: '暂无K线数据', left: 'center', top: 'center', textStyle: { color: '#666', fontSize: 16 } }
    })
    return
  }

  // 按时间升序排列
  const sorted = [...rawData].sort((a, b) => (a.date || '').localeCompare(b.date || ''))
  const dates = sorted.map((d) => (d.date || '').slice(0, 16))
  const closes = sorted.map((d) => d.close || 0)
  const volumes = sorted.map((d) => d.volume || d.vol || 0)
  const opens = sorted.map((d) => d.open || 0)

  // 分离涨跌段：涨(close>=prev)用红色，跌用绿色
  const upPrices = []
  const downPrices = []
  const upVols = []
  const downVols = []
  const upDots = []
  const downDots = []

  for (let i = 0; i < closes.length; i++) {
    const prevClose = i > 0 ? closes[i - 1] : opens[i]
    const isUp = closes[i] >= prevClose
    if (isUp) {
      upPrices.push(closes[i])
      downPrices.push(null)
      upDots.push(closes[i])
      downDots.push(null)
      upVols.push(volumes[i])
      downVols.push(null)
    } else {
      upPrices.push(null)
      downPrices.push(closes[i])
      upDots.push(null)
      downDots.push(closes[i])
      upVols.push(null)
      downVols.push(volumes[i])
    }
  }

  // 修复颜色切换点的断线：新颜色从上一个点开始，保证线段连续
  for (let i = 1; i < closes.length; i++) {
    const prevUp = closes[i - 1] >= (i > 1 ? closes[i - 2] : opens[i - 1])
    const currUp = closes[i] >= closes[i - 1]
    if (prevUp !== currUp) {
      if (currUp) {
        upPrices[i - 1] = closes[i - 1]
        upDots[i - 1] = closes[i - 1]
      } else {
        downPrices[i - 1] = closes[i - 1]
        downDots[i - 1] = closes[i - 1]
      }
    }
  }

  const option = {
    backgroundColor: 'transparent',
    grid: [
      { left: '4%', right: '4%', top: '5%', height: '55%' },
      { left: '4%', right: '4%', top: '68%', height: '22%' },
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#333' } },
        axisLabel: { color: '#888', fontSize: 10, rotate: 30 },
        gridIndex: 0,
      },
      {
        type: 'category',
        data: dates,
        boundaryGap: false,
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
      // 上涨线（红色）
      {
        name: '上涨',
        type: 'line',
        data: upPrices,
        smooth: true,
        connectNulls: false,
        symbol: 'none',
        symbolSize: 4,
        lineStyle: { color: '#e63946', width: 2 },
        itemStyle: { color: '#e63946' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(230,57,70,0.25)' },
            { offset: 1, color: 'rgba(230,57,70,0.01)' },
          ]),
        },
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
      // 下跌线（绿色）
      {
        name: '下跌',
        type: 'line',
        data: downPrices,
        smooth: true,
        connectNulls: false,
        symbol: 'none',
        symbolSize: 4,
        lineStyle: { color: '#22c55e', width: 2 },
        itemStyle: { color: '#22c55e' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(34,197,94,0.25)' },
            { offset: 1, color: 'rgba(34,197,94,0.01)' },
          ]),
        },
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
      // 上涨成交量（红）
      {
        name: '量-涨',
        type: 'bar',
        data: upVols,
        itemStyle: { color: 'rgba(230,57,70,0.55)' },
        xAxisIndex: 1,
        yAxisIndex: 1,
      },
      // 下跌成交量（绿）
      {
        name: '量-跌',
        type: 'bar',
        data: downVols,
        itemStyle: { color: 'rgba(34,197,94,0.55)' },
        xAxisIndex: 1,
        yAxisIndex: 1,
      },
    ],
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(26,26,26,0.95)',
      borderColor: '#333',
      textStyle: { color: '#e8e8e8', fontSize: 12 },
      formatter: (params) => {
        const p = params.filter((x) => x.value !== null && x.value !== undefined)
        if (!p.length) return ''
        let html = `<div style="font-weight:bold;margin-bottom:4px">${p[0].axisValue}</div>`
        p.forEach((item) => {
          if (item.seriesName.includes('量')) {
            html += `<div>${item.marker} ${item.seriesName}: ${(item.value / 10000).toFixed(0)}万手</div>`
          } else {
            html += `<div>${item.marker} ${item.seriesName}: ${item.value?.toFixed(2)}</div>`
          }
        })
        return html
      },
    },
  }

  klineChartInstance.setOption(option)
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

// 巨潮资讯网
function onCninfoSearch() {
  cninfoPage.value = 1
  fetchCninfoAnnouncements()
}

async function fetchCninfoAnnouncements() {
  cninfoLoading.value = true
  try {
    const { data } = await cninfoAnnouncements({
      stock_code: cninfoStockCode.value,
      keyword: cninfoKeyword.value,
      start_date: cninfoStartDate.value,
      end_date: cninfoEndDate.value,
      category: cninfoCategory.value,
      page_num: cninfoPage.value,
      page_size: cninfoPageSize.value,
    })
    if (data.status === 'success') {
      cninfoData.value = data.data || []
      cninfoTotal.value = data.total || 0
    }
  } finally {
    cninfoLoading.value = false
  }
}

function openPdf(url) {
  if (url) window.open(url, '_blank')
}

function formatTimestamp(ts) {
  if (!ts) return '--'
  const d = new Date(ts)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}`
}

function cninfoGoPage(p) {
  cninfoPage.value = p
  fetchCninfoAnnouncements()
}

// 巴菲特先知 - 交互式对话
import MarkdownIt from 'markdown-it'
const md = new MarkdownIt({ html: false, breaks: true })

function scrollChatBottom() {
  nextTick(() => {
    const el = chatMessagesRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function clearStockCode() {
  buffettStockCode.value = ''
}

async function sendMessage(presetMsg) {
  const msg = presetMsg || buffettInput.value.trim()
  if (!msg) return

  // 从消息中自动提取6位股票代码
  let stockCode = ''
  const match = msg.match(/\b(\d{6})\b/)
  if (match) {
    stockCode = match[1]
    if (stockCode !== buffettStockCode.value) {
      buffettStockCode.value = stockCode
    }
  }

  buffettMessages.value.push({ role: 'user', content: msg })
  buffettMessages.value.push({ role: 'assistant', content: '', rendered: '', score: null })
  buffettInput.value = ''
  buffettLoading.value = true
  scrollChatBottom()

  const aiMsg = buffettMessages.value[buffettMessages.value.length - 1]

  try {
    const response = await fetch('/api/analysis/buffett-oracle/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: buffettSessionId.value, message: msg, stock_code: stockCode }),
    })

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}))
      throw new Error(errData.detail || 'HTTP ' + response.status)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6))
          if (event.type === 'token') {
            aiMsg.content += event.content
            aiMsg.rendered = md.render(aiMsg.content)
            scrollChatBottom()
          } else if (event.type === 'context') {
            buffettSessionId.value = event.session_id
            buffettStockCode.value = event.stock_code
          } else if (event.type === 'done') {
            buffettSessionId.value = event.session_id
            aiMsg.score = event.score
            aiMsg.rendered = md.render(aiMsg.content)
          } else if (event.type === 'error') {
            aiMsg.content = event.message || 'AI 响应失败'
            aiMsg.rendered = md.render('**错误**: ' + aiMsg.content)
          }
        } catch { /* ignore parse errors */ }
      }
    }
  } catch (e) {
    aiMsg.content = '网络请求失败: ' + (e.message || '未知错误')
    aiMsg.rendered = md.render('**网络错误**: ' + aiMsg.content)
  } finally {
    buffettLoading.value = false
    scrollChatBottom()
  }
}

async function refreshAll() {
  refreshing.value = true
  await fetchOverview()
  await fetchTencentQuote()
  refreshing.value = false
}

// ===== 生命周期 =====
let overviewTimer = null

function isMarketHours() {
  const now = new Date()
  const day = now.getDay()
  if (day === 0 || day === 6) return false
  const h = now.getHours()
  const m = now.getMinutes()
  const t = h * 60 + m
  return t >= 9 * 60 && t <= 15 * 60
}

function scheduledPoll() {
  if (isMarketHours()) {
    fetchOverview()
  }
}

onMounted(() => {
  fetchOverview()
  fetchTencentQuote()
  overviewTimer = setInterval(scheduledPoll, 2000)
})

onUnmounted(() => {
  if (overviewTimer) clearInterval(overviewTimer)
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
  grid-template-columns: repeat(7, 1fr);
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
