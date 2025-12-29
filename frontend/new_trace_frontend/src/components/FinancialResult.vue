<template>
  <div class="financial-result">
    <!-- 置信度标签 -->
    <div class="badges-container">
      <div class="confidence-badge" :class="confidenceClass">
        {{ confidenceText }}
      </div>
      <div class="stock-badge">
        <el-icon><OfficeBuilding /></el-icon>
        <span>{{ result.stock_code }}{{ result.stock_name ? ` - ${result.stock_name}` : '' }}</span>
      </div>
      <div class="period-badge">
        <el-icon><Calendar /></el-icon>
        <span>{{ result.analysis_period }}</span>
      </div>
    </div>

    <!-- 股票信息 -->
    <div class="stock-info">
      <h3 class="stock-title">
        <el-icon><OfficeBuilding /></el-icon>
        {{ result.stock_code }}{{ result.stock_name ? ` - ${result.stock_name}` : '' }}
      </h3>
      <div class="info-row">
        <span>分析期间: {{ result.analysis_period }}</span>
        <span>数据点数: {{ result.data_points }}</span>
      </div>
    </div>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab" class="result-tabs">
      <!-- 综合评估 -->
      <el-tab-pane name="overview">
        <template #label>
          <el-icon><DataAnalysis /></el-icon>
          <span>综合评估</span>
        </template>
        <div class="overview-section">
          <div class="assessment-content">
            <h4>
              <el-icon><InfoFilled /></el-icon>
              投资建议与评估
            </h4>
            <div class="assessment-text">{{ result.overall_assessment }}</div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 价格统计 -->
      <el-tab-pane name="price">
        <template #label>
          <el-icon><DataAnalysis /></el-icon>
          <span>价格统计</span>
        </template>
        <div class="price-section">
          <h4>
            <el-icon><DataAnalysis /></el-icon>
            价格统计信息
          </h4>
          <!-- 价格统计卡片 -->
          <div class="stats-grid">
            <el-card class="stat-card highlight-card">
              <div class="stat-label">当前价格</div>
              <div class="stat-value price-value">{{ formatPrice(priceStats.current_price) }}</div>
              <div class="stat-trend" :class="priceStats.price_change >= 0 ? 'trend-up' : 'trend-down'">
                <el-icon v-if="priceStats.price_change >= 0"><ArrowUp /></el-icon>
                <el-icon v-else><ArrowDown /></el-icon>
                <span>{{ formatPercentage(Math.abs(priceStats.price_change_pct || 0)) }}</span>
              </div>
            </el-card>
            <el-card class="stat-card">
              <div class="stat-label">最高价</div>
              <div class="stat-value">{{ formatPrice(priceStats.highest_price) }}</div>
            </el-card>
            <el-card class="stat-card">
              <div class="stat-label">最低价</div>
              <div class="stat-value">{{ formatPrice(priceStats.lowest_price) }}</div>
            </el-card>
            <el-card class="stat-card">
              <div class="stat-label">平均价</div>
              <div class="stat-value">{{ formatPrice(priceStats.average_price) }}</div>
            </el-card>
            <el-card class="stat-card" :class="priceStats.price_change >= 0 ? 'positive' : 'negative'">
              <div class="stat-label">价格变化</div>
              <div class="stat-value">
                {{ formatPrice(priceStats.price_change) }}
                <span class="percentage">({{ formatPercentage(priceStats.price_change_pct) }})</span>
              </div>
            </el-card>
            <el-card class="stat-card">
              <div class="stat-label">波动率</div>
              <div class="stat-value">{{ formatPrice(priceStats.volatility) }}</div>
            </el-card>
          </div>
          <!-- 价格走势图 -->
          <el-card class="chart-card">
            <div class="chart-title">价格走势分析</div>
            <div ref="priceChartRef" class="chart-container"></div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 成交量统计 -->
      <el-tab-pane name="volume">
        <template #label>
          <el-icon><DataAnalysis /></el-icon>
          <span>成交量统计</span>
        </template>
        <div class="volume-section">
          <h4>
            <el-icon><DataAnalysis /></el-icon>
            成交量统计信息
          </h4>
          <!-- 成交量统计卡片 -->
          <div class="stats-grid">
            <el-card class="stat-card highlight-card">
              <div class="stat-label">总成交量</div>
              <div class="stat-value volume-value">{{ formatVolume(volumeStats.total_volume) }}</div>
            </el-card>
            <el-card class="stat-card">
              <div class="stat-label">平均成交量</div>
              <div class="stat-value">{{ formatVolume(volumeStats.average_volume) }}</div>
            </el-card>
            <el-card class="stat-card">
              <div class="stat-label">最大成交量</div>
              <div class="stat-value">{{ formatVolume(volumeStats.max_volume) }}</div>
            </el-card>
            <el-card class="stat-card">
              <div class="stat-label">最小成交量</div>
              <div class="stat-value">{{ formatVolume(volumeStats.min_volume) }}</div>
            </el-card>
            <el-card class="stat-card" :class="volumeTrendClass">
              <div class="stat-label">成交量趋势</div>
              <div class="stat-value">{{ volumeTrendText }}</div>
              <div class="trend-indicator" :class="volumeTrendClass">
                <el-icon v-if="volumeStats.volume_trend === 'increasing'"><TrendCharts /></el-icon>
                <el-icon v-else-if="volumeStats.volume_trend === 'decreasing'"><Bottom /></el-icon>
                <el-icon v-else><Minus /></el-icon>
              </div>
            </el-card>
          </div>
          <!-- 成交量对比图 -->
          <el-card class="chart-card">
            <div class="chart-title">成交量对比分析</div>
            <div ref="volumeChartRef" class="chart-container"></div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 技术指标 -->
      <el-tab-pane name="indicators">
        <template #label>
          <el-icon><Operation /></el-icon>
          <span>技术指标</span>
        </template>
        <div class="indicators-section">
          <h4>
            <el-icon><Operation /></el-icon>
            技术指标
          </h4>
          <!-- 技术指标卡片 -->
          <div class="indicators-grid">
            <el-card class="indicator-card">
              <div class="indicator-card-header">
                <h5>移动平均线 (MA)</h5>
                <el-icon><TrendCharts /></el-icon>
              </div>
              <div class="indicator-list">
                <div class="indicator-item">
                  <span class="indicator-label">MA5:</span>
                  <span class="indicator-value ma5">{{ formatIndicator(technicalIndicators.ma5) }}</span>
                </div>
                <div class="indicator-item">
                  <span class="indicator-label">MA10:</span>
                  <span class="indicator-value ma10">{{ formatIndicator(technicalIndicators.ma10) }}</span>
                </div>
                <div class="indicator-item">
                  <span class="indicator-label">MA20:</span>
                  <span class="indicator-value ma20">{{ formatIndicator(technicalIndicators.ma20) }}</span>
                </div>
                <div class="indicator-item">
                  <span class="indicator-label">MA30:</span>
                  <span class="indicator-value ma30">{{ formatIndicator(technicalIndicators.ma30) }}</span>
                </div>
                <div class="indicator-item">
                  <span class="indicator-label">MA60:</span>
                  <span class="indicator-value ma60">{{ formatIndicator(technicalIndicators.ma60) }}</span>
                </div>
              </div>
            </el-card>
            <el-card class="indicator-card">
              <div class="indicator-card-header">
                <h5>相对强弱指标 (RSI)</h5>
                <el-icon><DataAnalysis /></el-icon>
              </div>
              <div class="rsi-container">
                <div class="rsi-value" :class="rsiClass">
                  <span class="rsi-number">{{ formatIndicator(technicalIndicators.rsi) }}</span>
                  <div class="rsi-gauge">
                    <el-progress 
                      :percentage="(technicalIndicators.rsi || 0)" 
                      :color="rsiColor"
                      :stroke-width="12"
                      :show-text="false"
                    />
                    <div class="rsi-zones">
                      <span class="zone oversold">超卖</span>
                      <span class="zone normal">正常</span>
                      <span class="zone overbought">超买</span>
                    </div>
                  </div>
                </div>
              </div>
            </el-card>
            <el-card class="indicator-card">
              <div class="indicator-card-header">
                <h5>MACD</h5>
                <el-icon><Operation /></el-icon>
              </div>
              <div class="indicator-list">
                <div class="indicator-item">
                  <span class="indicator-label">MACD:</span>
                  <span class="indicator-value" :class="technicalIndicators.macd >= 0 ? 'positive' : 'negative'">
                    {{ formatIndicator(technicalIndicators.macd) }}
                  </span>
                </div>
                <div class="indicator-item">
                  <span class="indicator-label">信号线:</span>
                  <span class="indicator-value">{{ formatIndicator(technicalIndicators.macd_signal) }}</span>
                </div>
                <div class="indicator-item">
                  <span class="indicator-label">柱状图:</span>
                  <span class="indicator-value" :class="technicalIndicators.macd_histogram >= 0 ? 'positive' : 'negative'">
                    {{ formatIndicator(technicalIndicators.macd_histogram) }}
                  </span>
                </div>
              </div>
              <div ref="macdChartRef" class="mini-chart"></div>
            </el-card>
            <el-card class="indicator-card">
              <div class="indicator-card-header">
                <h5>布林带 (Bollinger Bands)</h5>
                <el-icon><Operation /></el-icon>
              </div>
              <div class="indicator-list">
                <div class="indicator-item">
                  <span class="indicator-label">上轨:</span>
                  <span class="indicator-value bollinger-upper">{{ formatIndicator(technicalIndicators.bollinger_upper) }}</span>
                </div>
                <div class="indicator-item">
                  <span class="indicator-label">中轨:</span>
                  <span class="indicator-value bollinger-middle">{{ formatIndicator(technicalIndicators.bollinger_middle) }}</span>
                </div>
                <div class="indicator-item">
                  <span class="indicator-label">下轨:</span>
                  <span class="indicator-value bollinger-lower">{{ formatIndicator(technicalIndicators.bollinger_lower) }}</span>
                </div>
              </div>
              <div ref="bollingerChartRef" class="mini-chart"></div>
            </el-card>
          </div>
          <!-- 技术指标综合图表 -->
          <el-card class="chart-card">
            <div class="chart-title">技术指标综合分析</div>
            <div ref="indicatorsChartRef" class="chart-container"></div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 交易信号 -->
      <el-tab-pane name="signals">
        <template #label>
          <el-icon><Bell /></el-icon>
          <span>交易信号</span>
        </template>
        <div class="signals-section">
          <h4>
            <el-icon><Bell /></el-icon>
            交易信号 ({{ tradingSignals.length }})
          </h4>
          <div v-if="tradingSignals.length === 0" class="empty-state">
            <div class="empty-icon">
              <el-icon :size="48"><Bell /></el-icon>
            </div>
            <p>暂无交易信号</p>
          </div>
          <div v-else class="signals-list">
            <el-card v-for="(signal, index) in tradingSignals" :key="index" class="signal-card" :class="`signal-${signal.signal_type}`">
              <div class="signal-header">
                <el-tag :type="signalTypeTagType(signal.signal_type)" size="large">
                  {{ signalTypeText(signal.signal_type) }}
                </el-tag>
                <div class="signal-strength">
                  <span>信号强度: </span>
                  <el-progress 
                    :percentage="signal.signal_strength * 100" 
                    :color="signalTypeColor(signal.signal_type)"
                    :stroke-width="8"
                    :show-text="false"
                  />
                  <span class="strength-value">{{ (signal.signal_strength * 100).toFixed(0) }}%</span>
                </div>
              </div>
              <div class="signal-reason">{{ signal.signal_reason }}</div>
              <div class="signal-meta">
                <span v-if="signal.signal_date">
                  <el-icon><Calendar /></el-icon>
                  {{ signal.signal_date }}
                </span>
                <span v-if="signal.indicators_used && signal.indicators_used.length > 0">
                  <el-icon><Operation /></el-icon>
                  指标: {{ signal.indicators_used.join(', ') }}
                </span>
              </div>
            </el-card>
          </div>
        </div>
      </el-tab-pane>

      <!-- 风险指标 -->
      <el-tab-pane name="risk">
        <template #label>
          <el-icon><Warning /></el-icon>
          <span>风险指标</span>
        </template>
        <div class="risk-section">
          <h4>
            <el-icon><Warning /></el-icon>
            风险指标
          </h4>
          <div class="stats-grid">
            <el-card class="stat-card">
              <div class="stat-label">波动率</div>
              <div class="stat-value">{{ formatPercentage(riskMetrics.volatility) }}</div>
            </el-card>
            <el-card class="stat-card">
              <div class="stat-label">最大回撤</div>
              <div class="stat-value negative">{{ formatPercentage(riskMetrics.max_drawdown) }}</div>
            </el-card>
            <el-card class="stat-card" v-if="riskMetrics.sharpe_ratio !== null">
              <div class="stat-label">夏普比率</div>
              <div class="stat-value">{{ formatIndicator(riskMetrics.sharpe_ratio) }}</div>
            </el-card>
            <el-card class="stat-card" :class="riskLevelClass">
              <div class="stat-label">风险等级</div>
              <div class="stat-value">{{ riskLevelText }}</div>
            </el-card>
          </div>
        </div>
      </el-tab-pane>

      <!-- 趋势分析 -->
      <el-tab-pane name="trend">
        <template #label>
          <el-icon><DataAnalysis /></el-icon>
          <span>趋势分析</span>
        </template>
        <div class="trend-section">
          <h4>
            <el-icon><DataAnalysis /></el-icon>
            趋势分析
          </h4>
          <div class="trend-grid">
            <el-card class="trend-card">
              <div class="trend-label">短期趋势</div>
              <div class="trend-value" :class="trendClass(trendAnalysis.short_term_trend)">
                {{ trendText(trendAnalysis.short_term_trend) }}
              </div>
            </el-card>
            <el-card class="trend-card">
              <div class="trend-label">中期趋势</div>
              <div class="trend-value" :class="trendClass(trendAnalysis.medium_term_trend)">
                {{ trendText(trendAnalysis.medium_term_trend) }}
              </div>
            </el-card>
            <el-card class="trend-card">
              <div class="trend-label">长期趋势</div>
              <div class="trend-value" :class="trendClass(trendAnalysis.long_term_trend)">
                {{ trendText(trendAnalysis.long_term_trend) }}
              </div>
            </el-card>
            <el-card class="trend-card">
              <div class="trend-label">趋势强度</div>
              <div class="trend-value">
                <el-progress 
                  :percentage="trendAnalysis.trend_strength * 100" 
                  :stroke-width="12"
                />
                <span class="strength-text">{{ (trendAnalysis.trend_strength * 100).toFixed(0) }}%</span>
              </div>
            </el-card>
            <el-card class="trend-card" v-if="trendAnalysis.support_level">
              <div class="trend-label">支撑位</div>
              <div class="trend-value">{{ formatPrice(trendAnalysis.support_level) }}</div>
            </el-card>
            <el-card class="trend-card" v-if="trendAnalysis.resistance_level">
              <div class="trend-label">阻力位</div>
              <div class="trend-value">{{ formatPrice(trendAnalysis.resistance_level) }}</div>
            </el-card>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { 
  DataAnalysis, Calendar, OfficeBuilding, InfoFilled, Operation, 
  Bell, Warning, ArrowUp, ArrowDown, TrendCharts, Bottom, Minus
} from '@element-plus/icons-vue'

const props = defineProps({
  result: {
    type: Object,
    required: true
  }
})

const activeTab = ref('overview')

// 图表引用
const priceChartRef = ref(null)
const volumeChartRef = ref(null)
const macdChartRef = ref(null)
const bollingerChartRef = ref(null)
const indicatorsChartRef = ref(null)

// ECharts 实例
let priceChart = null
let volumeChart = null
let macdChart = null
let bollingerChart = null
let indicatorsChart = null

// 计算属性
const priceStats = computed(() => props.result.price_stats || {})
const volumeStats = computed(() => props.result.volume_stats || {})
const technicalIndicators = computed(() => props.result.technical_indicators || {})
const tradingSignals = computed(() => props.result.trading_signals || [])
const riskMetrics = computed(() => props.result.risk_metrics || {})
const trendAnalysis = computed(() => props.result.trend_analysis || {})

// 置信度
const confidenceText = computed(() => {
  const score = props.result.confidence_score || 0
  return `置信度: ${(score * 100).toFixed(0)}%`
})

const confidenceClass = computed(() => {
  const score = props.result.confidence_score || 0
  if (score >= 0.8) return 'high'
  if (score >= 0.6) return 'medium'
  return 'low'
})

// 成交量趋势
const volumeTrendText = computed(() => {
  const trend = volumeStats.value.volume_trend
  const map = {
    'increasing': '上升',
    'decreasing': '下降',
    'stable': '稳定'
  }
  return map[trend] || trend
})

const volumeTrendClass = computed(() => {
  const trend = volumeStats.value.volume_trend
  if (trend === 'increasing') return 'positive'
  if (trend === 'decreasing') return 'negative'
  return 'neutral'
})

// RSI 分类
const rsiClass = computed(() => {
  const rsi = technicalIndicators.value.rsi
  if (!rsi) return ''
  if (rsi < 30) return 'oversold'
  if (rsi > 70) return 'overbought'
  return 'normal'
})

// 风险等级
const riskLevelText = computed(() => {
  const level = riskMetrics.value.risk_level
  const map = {
    'low': '低风险',
    'medium': '中风险',
    'high': '高风险'
  }
  return map[level] || level
})

const riskLevelClass = computed(() => {
  const level = riskMetrics.value.risk_level
  return `risk-${level}`
})

// 格式化函数
const formatPrice = (value) => {
  if (value === null || value === undefined) return 'N/A'
  return value.toFixed(2)
}

const formatVolume = (value) => {
  if (value === null || value === undefined) return 'N/A'
  if (value >= 100000000) return (value / 100000000).toFixed(2) + '亿'
  if (value >= 10000) return (value / 10000).toFixed(2) + '万'
  return value.toFixed(0)
}

const formatPercentage = (value) => {
  if (value === null || value === undefined) return 'N/A'
  return value.toFixed(2) + '%'
}

const formatIndicator = (value) => {
  if (value === null || value === undefined) return 'N/A'
  return value.toFixed(2)
}

// 交易信号
const signalTypeText = (type) => {
  const map = {
    'buy': '买入',
    'sell': '卖出',
    'hold': '持有'
  }
  return map[type] || type
}

const signalTypeTagType = (type) => {
  const map = {
    'buy': 'success',
    'sell': 'danger',
    'hold': 'info'
  }
  return map[type] || 'info'
}

const signalTypeColor = (type) => {
  const map = {
    'buy': '#67c23a',
    'sell': '#f56c6c',
    'hold': '#909399'
  }
  return map[type] || '#909399'
}

// 趋势
const trendText = (trend) => {
  const map = {
    'up': '上涨',
    'down': '下跌',
    'sideways': '横盘'
  }
  return map[trend] || trend
}

const trendClass = (trend) => {
  if (trend === 'up') return 'trend-up'
  if (trend === 'down') return 'trend-down'
  return 'trend-sideways'
}

// RSI 颜色
const rsiColor = computed(() => {
  const rsi = technicalIndicators.value.rsi
  if (!rsi) return '#909399'
  if (rsi < 30) return '#67c23a' // 超卖 - 绿色
  if (rsi > 70) return '#f56c6c' // 超买 - 红色
  return '#409eff' // 正常 - 蓝色
})

// 加载 ECharts
const loadECharts = () => {
  return new Promise((resolve) => {
    if (window.echarts) {
      resolve(window.echarts)
      return
    }
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'
    script.onload = () => resolve(window.echarts)
    script.onerror = () => {
      console.error('Failed to load ECharts')
      resolve(null)
    }
    document.head.appendChild(script)
  })
}

// 从真实历史数据中提取价格数据
const getPriceData = () => {
  const historicalData = props.result.historical_data || []
  
  if (historicalData.length === 0) {
    // 如果没有历史数据，返回空数据
    return { dates: [], data: [], current: 0, high: 0, low: 0, avg: 0 }
  }
  
  const dates = historicalData.map(item => {
    const date = new Date(item.date)
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  })
  const data = historicalData.map(item => parseFloat(item.close.toFixed(2)))
  const current = historicalData.length > 0 ? historicalData[historicalData.length - 1].close : 0
  const high = priceStats.value.highest_price || Math.max(...data)
  const low = priceStats.value.lowest_price || Math.min(...data)
  const avg = priceStats.value.average_price || (data.reduce((a, b) => a + b, 0) / data.length)
  
  return { dates, data, current, high, low, avg }
}

// 从真实历史数据中提取成交量数据
const getVolumeData = () => {
  const historicalData = props.result.historical_data || []
  
  if (historicalData.length === 0) {
    // 如果没有历史数据，返回空数据
    return { dates: [], data: [], avg: 0, max: 0, min: 0 }
  }
  
  const dates = historicalData.map(item => {
    const date = new Date(item.date)
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  })
  const data = historicalData.map(item => item.volume)
  const avg = volumeStats.value.average_volume || (data.reduce((a, b) => a + b, 0) / data.length)
  const max = volumeStats.value.max_volume || Math.max(...data)
  const min = volumeStats.value.min_volume || Math.min(...data)
  
  return { dates, data, avg, max, min }
}

// 初始化价格图表
const initPriceChart = async () => {
  if (!priceChartRef.value) return
  
  const echarts = await loadECharts()
  if (!echarts) return
  
  if (priceChart) {
    priceChart.dispose()
  }
  
  priceChart = echarts.init(priceChartRef.value)
  const { dates, data, current, high, low, avg } = getPriceData()
  
  if (dates.length === 0) {
    priceChart.setOption({
      title: {
        text: '暂无历史数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#999', fontSize: 14 }
      }
    })
    return
  }
  
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const param = params[0]
        return `${param.name}<br/>价格: ¥${param.value.toFixed(2)}`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLabel: {
        rotate: 45,
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      name: '价格 (¥)',
      axisLabel: {
        formatter: '¥{value}'
      }
    },
    series: [
      {
        name: '价格',
        type: 'line',
        smooth: true,
        data: data,
        lineStyle: {
          color: '#667eea',
          width: 2
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(102, 126, 234, 0.3)' },
              { offset: 1, color: 'rgba(102, 126, 234, 0.05)' }
            ]
          }
        },
        markLine: {
          data: [
            { yAxis: high, name: '最高价', lineStyle: { color: '#67c23a', type: 'dashed' } },
            { yAxis: low, name: '最低价', lineStyle: { color: '#f56c6c', type: 'dashed' } },
            { yAxis: avg, name: '平均价', lineStyle: { color: '#e6a23c', type: 'dashed' } }
          ]
        }
      }
    ]
  }
  
  priceChart.setOption(option)
  
  // 响应式调整
  window.addEventListener('resize', () => {
    priceChart?.resize()
  })
}

// 初始化成交量图表
const initVolumeChart = async () => {
  if (!volumeChartRef.value) return
  
  const echarts = await loadECharts()
  if (!echarts) return
  
  if (volumeChart) {
    volumeChart.dispose()
  }
  
  volumeChart = echarts.init(volumeChartRef.value)
  const { dates, data, avg } = getVolumeData()
  
  if (dates.length === 0) {
    volumeChart.setOption({
      title: {
        text: '暂无历史数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#999', fontSize: 14 }
      }
    })
    return
  }
  
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const param = params[0]
        return `${param.name}<br/>成交量: ${formatVolume(parseFloat(param.value))}`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45,
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      name: '成交量',
      axisLabel: {
        formatter: (value) => formatVolume(value)
      }
    },
    series: [
      {
        name: '成交量',
        type: 'bar',
        data: data,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#83bff6' },
            { offset: 0.5, color: '#188df0' },
            { offset: 1, color: '#188df0' }
          ])
        },
        markLine: {
          data: [
            { yAxis: avg, name: '平均成交量', lineStyle: { color: '#e6a23c', type: 'dashed' } }
          ]
        }
      }
    ]
  }
  
  volumeChart.setOption(option)
  
  window.addEventListener('resize', () => {
    volumeChart?.resize()
  })
}

// 初始化 MACD 迷你图表
const initMACDChart = async () => {
  if (!macdChartRef.value) return
  
  const echarts = await loadECharts()
  if (!echarts) return
  
  if (macdChart) {
    macdChart.dispose()
  }
  
  macdChart = echarts.init(macdChartRef.value)
  const macd = technicalIndicators.value.macd || 0
  const signal = technicalIndicators.value.macd_signal || 0
  const histogram = technicalIndicators.value.macd_histogram || 0
  
  const option = {
    tooltip: { trigger: 'axis' },
    grid: { left: '10%', right: '10%', top: '10%', bottom: '10%' },
    xAxis: { type: 'category', data: ['MACD', '信号线', '柱状图'], axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: [macd, signal, histogram],
        itemStyle: {
          color: (params) => {
            const colors = ['#667eea', '#e6a23c', histogram >= 0 ? '#67c23a' : '#f56c6c']
            return colors[params.dataIndex]
          }
        }
      }
    ]
  }
  
  macdChart.setOption(option)
}

// 初始化布林带迷你图表
const initBollingerChart = async () => {
  if (!bollingerChartRef.value) return
  
  const echarts = await loadECharts()
  if (!echarts) return
  
  if (bollingerChart) {
    bollingerChart.dispose()
  }
  
  bollingerChart = echarts.init(bollingerChartRef.value)
  const upper = technicalIndicators.value.bollinger_upper || 0
  const middle = technicalIndicators.value.bollinger_middle || 0
  const lower = technicalIndicators.value.bollinger_lower || 0
  const current = priceStats.value.current_price || middle
  
  const option = {
    tooltip: { trigger: 'axis' },
    grid: { left: '10%', right: '10%', top: '10%', bottom: '10%' },
    xAxis: { type: 'category', data: ['上轨', '中轨', '下轨', '当前价'], axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: [upper, middle, lower, current],
        itemStyle: {
          color: (params) => {
            const colors = ['#f56c6c', '#e6a23c', '#67c23a', '#667eea']
            return colors[params.dataIndex]
          }
        }
      }
    ]
  }
  
  bollingerChart.setOption(option)
}

// 初始化技术指标综合图表
const initIndicatorsChart = async () => {
  if (!indicatorsChartRef.value) return
  
  const echarts = await loadECharts()
  if (!echarts) return
  
  if (indicatorsChart) {
    indicatorsChart.dispose()
  }
  
  indicatorsChart = echarts.init(indicatorsChartRef.value)
  const historicalData = props.result.historical_data || []
  
  if (historicalData.length === 0) {
    indicatorsChart.setOption({
      title: {
        text: '暂无历史数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#999', fontSize: 14 }
      }
    })
    return
  }
  
  const dates = historicalData.map(item => {
    const date = new Date(item.date)
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  })
  
  const closeData = historicalData.map(item => item.close)
  const ma5Data = historicalData.map(item => item.ma5).filter(v => v !== null && v !== undefined)
  const ma10Data = historicalData.map(item => item.ma10).filter(v => v !== null && v !== undefined)
  const ma20Data = historicalData.map(item => item.ma20).filter(v => v !== null && v !== undefined)
  const ma30Data = historicalData.map(item => item.ma30).filter(v => v !== null && v !== undefined)
  const ma60Data = historicalData.map(item => item.ma60).filter(v => v !== null && v !== undefined)
  
  const option = {
    tooltip: { 
      trigger: 'axis',
      formatter: (params) => {
        let result = `${params[0].name}<br/>`
        params.forEach(param => {
          if (param.value !== null && param.value !== undefined) {
            result += `${param.seriesName}: ¥${param.value.toFixed(2)}<br/>`
          }
        })
        return result
      }
    },
    legend: {
      data: ['收盘价', 'MA5', 'MA10', 'MA20', 'MA30', 'MA60'],
      bottom: 0
    },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '3%', containLabel: true },
    xAxis: { 
      type: 'category', 
      data: dates,
      axisLabel: {
        rotate: 45,
        fontSize: 10
      }
    },
    yAxis: { type: 'value', name: '价格 (¥)' },
    series: [
      { 
        name: '收盘价', 
        type: 'line', 
        data: closeData, 
        lineStyle: { color: '#667eea', width: 2 },
        smooth: true
      },
      { 
        name: 'MA5', 
        type: 'line', 
        data: ma5Data.length > 0 ? ma5Data : null, 
        lineStyle: { color: '#f56c6c', width: 1.5 },
        smooth: true
      },
      { 
        name: 'MA10', 
        type: 'line', 
        data: ma10Data.length > 0 ? ma10Data : null, 
        lineStyle: { color: '#e6a23c', width: 1.5 },
        smooth: true
      },
      { 
        name: 'MA20', 
        type: 'line', 
        data: ma20Data.length > 0 ? ma20Data : null, 
        lineStyle: { color: '#67c23a', width: 1.5 },
        smooth: true
      },
      { 
        name: 'MA30', 
        type: 'line', 
        data: ma30Data.length > 0 ? ma30Data : null, 
        lineStyle: { color: '#409eff', width: 1.5 },
        smooth: true
      },
      { 
        name: 'MA60', 
        type: 'line', 
        data: ma60Data.length > 0 ? ma60Data : null, 
        lineStyle: { color: '#909399', width: 1.5 },
        smooth: true
      }
    ]
  }
  
  indicatorsChart.setOption(option)
  
  window.addEventListener('resize', () => {
    indicatorsChart?.resize()
  })
}

// 监听标签页切换
watch(activeTab, async (newTab) => {
  await nextTick()
  if (newTab === 'price') {
    initPriceChart()
  } else if (newTab === 'volume') {
    initVolumeChart()
  } else if (newTab === 'indicators') {
    initMACDChart()
    initBollingerChart()
    initIndicatorsChart()
  }
})

onMounted(async () => {
  await nextTick()
  if (activeTab.value === 'price') {
    initPriceChart()
  } else if (activeTab.value === 'volume') {
    initVolumeChart()
  } else if (activeTab.value === 'indicators') {
    initMACDChart()
    initBollingerChart()
    initIndicatorsChart()
  }
})
</script>

<style scoped>
.financial-result {
  padding: 20px;
}

.badges-container {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.confidence-badge {
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
}

.confidence-badge.high {
  background: #e8f5e9;
  color: #2e7d32;
}

.confidence-badge.medium {
  background: #fff3e0;
  color: #e65100;
}

.confidence-badge.low {
  background: #ffebee;
  color: #c62828;
}

.stock-badge,
.period-badge {
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
  background: #f5f5f5;
  color: #666;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.stock-info {
  margin-bottom: 20px;
  padding: 16px;
  background: #f9f9f9;
  border-radius: 8px;
}

.stock-title {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #2d3748;
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-row {
  display: flex;
  gap: 20px;
  font-size: 14px;
  color: #666;
}

.result-tabs {
  margin-top: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.stat-card {
  text-align: center;
}

.stat-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #2d3748;
}

.stat-value.positive {
  color: #67c23a;
}

.stat-value.negative {
  color: #f56c6c;
}

.price-value {
  font-size: 24px;
  color: #667eea;
}

.percentage {
  font-size: 14px;
  margin-left: 4px;
}

.indicators-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-top: 16px;
}

.indicator-group {
  padding: 16px;
  background: #f9f9f9;
  border-radius: 8px;
}

.indicator-group h5 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #2d3748;
}

.indicator-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.indicator-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.indicator-label {
  color: #666;
}

.indicator-value {
  font-weight: 500;
  color: #2d3748;
}

.indicator-value.oversold {
  color: #67c23a;
}

.indicator-value.overbought {
  color: #f56c6c;
}

.signals-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.signal-card {
  border-left: 4px solid #ddd;
}

.signal-card.signal-buy {
  border-left-color: #67c23a;
}

.signal-card.signal-sell {
  border-left-color: #f56c6c;
}

.signal-card.signal-hold {
  border-left-color: #909399;
}

.signal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.signal-strength {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  max-width: 300px;
  margin-left: 16px;
}

.strength-value {
  font-size: 12px;
  color: #666;
  min-width: 40px;
}

.signal-reason {
  font-size: 14px;
  color: #2d3748;
  margin-bottom: 8px;
}

.signal-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #999;
}

.trend-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.trend-card {
  text-align: center;
}

.trend-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}

.trend-value {
  font-size: 18px;
  font-weight: 600;
}

.trend-value.trend-up {
  color: #67c23a;
}

.trend-value.trend-down {
  color: #f56c6c;
}

.trend-value.trend-sideways {
  color: #909399;
}

.strength-text {
  margin-left: 8px;
  font-size: 14px;
  color: #666;
}

.risk-low {
  border-left: 4px solid #67c23a;
}

.risk-medium {
  border-left: 4px solid #e6a23c;
}

.risk-high {
  border-left: 4px solid #f56c6c;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
}

.empty-icon {
  margin-bottom: 16px;
}

.assessment-content {
  margin-top: 16px;
}

.assessment-content h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
  display: flex;
  align-items: center;
  gap: 8px;
}

.assessment-text {
  line-height: 1.8;
  color: #2d3748;
  white-space: pre-wrap;
}

/* 高亮卡片样式 */
.highlight-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.highlight-card .stat-label {
  color: rgba(255, 255, 255, 0.9);
}

.highlight-card .stat-value {
  color: #ffffff;
  font-size: 28px;
}

.highlight-card .price-value {
  font-size: 32px;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: 12px;
  font-weight: 500;
}

.stat-trend.trend-up {
  color: #67c23a;
}

.stat-trend.trend-down {
  color: #f56c6c;
}

.volume-value {
  font-size: 24px;
  color: #667eea;
}

.trend-indicator {
  margin-top: 8px;
  font-size: 20px;
}

.trend-indicator.positive {
  color: #67c23a;
}

.trend-indicator.negative {
  color: #f56c6c;
}

.trend-indicator.neutral {
  color: #909399;
}

/* 图表卡片样式 */
.chart-card {
  margin-top: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f0f0f0;
}

.chart-container {
  width: 100%;
  height: 400px;
  min-height: 400px;
}

.mini-chart {
  width: 100%;
  height: 120px;
  margin-top: 12px;
}

/* 技术指标卡片美化 */
.indicator-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: all 0.3s;
  border: 1px solid #f0f0f0;
}

.indicator-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.indicator-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.indicator-card-header h5 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #2d3748;
}

.indicator-card-header .el-icon {
  font-size: 20px;
  color: #667eea;
}

/* RSI 容器样式 */
.rsi-container {
  padding: 16px 0;
}

.rsi-value {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.rsi-number {
  font-size: 32px;
  font-weight: 700;
  color: #2d3748;
}

.rsi-value.oversold .rsi-number {
  color: #67c23a;
}

.rsi-value.overbought .rsi-number {
  color: #f56c6c;
}

.rsi-gauge {
  width: 100%;
  padding: 0 20px;
}

.rsi-zones {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 11px;
  color: #999;
}

.rsi-zones .zone {
  flex: 1;
  text-align: center;
}

/* 移动平均线颜色 */
.indicator-value.ma5 {
  color: #f56c6c;
  font-weight: 600;
}

.indicator-value.ma10 {
  color: #e6a23c;
  font-weight: 600;
}

.indicator-value.ma20 {
  color: #67c23a;
  font-weight: 600;
}

.indicator-value.ma30 {
  color: #409eff;
  font-weight: 600;
}

.indicator-value.ma60 {
  color: #909399;
  font-weight: 600;
}

/* 布林带颜色 */
.indicator-value.bollinger-upper {
  color: #f56c6c;
  font-weight: 600;
}

.indicator-value.bollinger-middle {
  color: #e6a23c;
  font-weight: 600;
}

.indicator-value.bollinger-lower {
  color: #67c23a;
  font-weight: 600;
}

/* 统计卡片增强 */
.stat-card {
  transition: all 0.3s;
  border-radius: 12px;
  border: 1px solid #f0f0f0;
}

.stat-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.stat-card.positive {
  border-left: 4px solid #67c23a;
}

.stat-card.negative {
  border-left: 4px solid #f56c6c;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .chart-container {
    height: 300px;
  }
  
  .stats-grid {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  }
  
  .indicators-grid {
    grid-template-columns: 1fr;
  }
}
</style>

