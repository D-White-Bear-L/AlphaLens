<template>
  <div class="backtest-result">
    <!-- 回测信息头部 -->
    <div class="backtest-header">
      <div class="header-info">
        <h3 class="stock-title">
          <el-icon><TrendCharts /></el-icon>
          {{ result.stock_code }}{{ result.stock_name ? ` - ${result.stock_name}` : '' }}
        </h3>
        <div class="info-row">
          <span>回测期间: {{ result.backtest_period }}</span>
          <span>策略类型: {{ strategyTypeText }}</span>
        </div>
      </div>
    </div>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab" class="result-tabs">
      <!-- 回测概览 -->
      <el-tab-pane name="overview">
        <template #label>
          <el-icon><DataAnalysis /></el-icon>
          <span>回测概览</span>
        </template>
        <div class="overview-section">
          <!-- 核心指标卡片 -->
          <div class="metrics-grid">
            <el-card class="metric-card highlight-card">
              <div class="metric-label">总收益率</div>
              <div class="metric-value" :class="returnRateClass">
                {{ formatPercentage(result.metrics.total_return_rate) }}
              </div>
              <div class="metric-sub">
                初始资金: ¥{{ formatNumber(result.metrics.initial_capital) }} → 
                最终资金: ¥{{ formatNumber(result.metrics.final_capital) }}
              </div>
            </el-card>
            
            <el-card class="metric-card">
              <div class="metric-label">总交易次数</div>
              <div class="metric-value">{{ result.metrics.total_trades }}</div>
              <div class="metric-sub">
                盈利: {{ result.metrics.successful_trades }} | 
                亏损: {{ result.metrics.failed_trades }}
              </div>
            </el-card>
            
            <el-card class="metric-card">
              <div class="metric-label">胜率</div>
              <div class="metric-value" :class="winRateClass">
                {{ formatPercentage(result.metrics.win_rate * 100) }}
              </div>
              <div class="metric-sub">
                平均盈亏: ¥{{ formatNumber(result.metrics.average_profit) }}
              </div>
            </el-card>
            
            <el-card class="metric-card">
              <div class="metric-label">最大回撤</div>
              <div class="metric-value negative">
                {{ formatPercentage(result.metrics.max_drawdown) }}
              </div>
              <div class="metric-sub">
                最大盈利: ¥{{ formatNumber(result.metrics.max_profit) }} | 
                最大亏损: ¥{{ formatNumber(result.metrics.max_loss) }}
              </div>
            </el-card>
          </div>
          
          <!-- 详细指标 -->
          <el-card class="detailed-metrics">
            <div class="metrics-title">
              <el-icon><Operation /></el-icon>
              详细指标
            </div>
            <div class="detailed-grid">
              <div class="metric-item">
                <span class="item-label">总收益:</span>
                <span class="item-value" :class="result.metrics.total_return >= 0 ? 'positive' : 'negative'">
                  ¥{{ formatNumber(result.metrics.total_return) }}
                </span>
              </div>
              <div class="metric-item" v-if="result.metrics.annualized_return_rate">
                <span class="item-label">年化收益率:</span>
                <span class="item-value" :class="result.metrics.annualized_return_rate >= 0 ? 'positive' : 'negative'">
                  {{ formatPercentage(result.metrics.annualized_return_rate) }}
                </span>
              </div>
              <div class="metric-item" v-if="result.metrics.sharpe_ratio">
                <span class="item-label">夏普比率:</span>
                <span class="item-value">{{ formatNumber(result.metrics.sharpe_ratio, 2) }}</span>
              </div>
              <div class="metric-item" v-if="result.metrics.profit_factor">
                <span class="item-label">盈亏比:</span>
                <span class="item-value">{{ formatNumber(result.metrics.profit_factor, 2) }}</span>
              </div>
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 资金曲线 -->
      <el-tab-pane name="equity">
        <template #label>
          <el-icon><TrendCharts /></el-icon>
          <span>资金曲线</span>
        </template>
        <div class="equity-section">
          <el-card class="chart-card">
            <div class="chart-title">资金曲线走势</div>
            <div ref="equityChartRef" class="chart-container"></div>
          </el-card>
          <el-card class="chart-card" style="margin-top: 20px;">
            <div class="chart-title">回撤曲线</div>
            <div ref="drawdownChartRef" class="chart-container"></div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 统计分析 -->
      <el-tab-pane name="analysis">
        <template #label>
          <el-icon><PieChart /></el-icon>
          <span>统计分析</span>
        </template>
        <div class="analysis-section">
          <div class="charts-grid">
            <el-card class="chart-card">
              <div class="chart-title">交易盈亏分布</div>
              <div ref="profitDistributionChartRef" class="chart-container"></div>
            </el-card>
            <el-card class="chart-card">
              <div class="chart-title">信号类型分布</div>
              <div ref="signalTypeChartRef" class="chart-container"></div>
            </el-card>
            <el-card class="chart-card">
              <div class="chart-title">持仓天数分布</div>
              <div ref="holdDaysChartRef" class="chart-container"></div>
            </el-card>
            <el-card class="chart-card">
              <div class="chart-title">月度收益统计</div>
              <div ref="monthlyReturnChartRef" class="chart-container"></div>
            </el-card>
          </div>
        </div>
      </el-tab-pane>

      <!-- 交易记录 -->
      <el-tab-pane name="trades">
        <template #label>
          <el-icon><List /></el-icon>
          <span>交易记录 ({{ result.trades.length }})</span>
        </template>
        <div class="trades-section">
          <div v-if="result.trades.length === 0" class="empty-state">
            <el-icon :size="48"><List /></el-icon>
            <p>暂无交易记录</p>
          </div>
          <el-table 
            v-else
            :data="result.trades" 
            stripe
            style="width: 100%"
            :default-sort="{ prop: 'trade_id', order: 'ascending' }"
          >
            <el-table-column prop="trade_id" label="交易ID" width="80" sortable />
            <el-table-column prop="buy_date" label="买入日期" width="120" />
            <el-table-column prop="buy_price" label="买入价" width="100">
              <template #default="{ row }">
                ¥{{ formatNumber(row.buy_price, 2) }}
              </template>
            </el-table-column>
            <el-table-column prop="sell_date" label="卖出日期" width="120" />
            <el-table-column prop="sell_price" label="卖出价" width="100">
              <template #default="{ row }">
                ¥{{ formatNumber(row.sell_price, 2) }}
              </template>
            </el-table-column>
            <el-table-column prop="shares" label="股数" width="100" />
            <el-table-column prop="hold_days" label="持有天数" width="100" />
            <el-table-column prop="profit" label="盈亏" width="120" sortable>
              <template #default="{ row }">
                <span :class="row.profit >= 0 ? 'positive' : 'negative'">
                  {{ row.profit >= 0 ? '+' : '' }}¥{{ formatNumber(row.profit, 2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="return_rate" label="收益率" width="100" sortable>
              <template #default="{ row }">
                <span :class="row.return_rate >= 0 ? 'positive' : 'negative'">
                  {{ row.return_rate >= 0 ? '+' : '' }}{{ formatPercentage(row.return_rate) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="signal_type" label="信号类型" width="100">
              <template #default="{ row }">
                <el-tag :type="signalTypeTagType(row.signal_type)" size="small">
                  {{ signalTypeText(row.signal_type) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { DataAnalysis, TrendCharts, Operation, List, PieChart } from '@element-plus/icons-vue'

const props = defineProps({
  result: {
    type: Object,
    required: true
  }
})

const activeTab = ref('overview')
const equityChartRef = ref(null)
const drawdownChartRef = ref(null)
const profitDistributionChartRef = ref(null)
const signalTypeChartRef = ref(null)
const holdDaysChartRef = ref(null)
const monthlyReturnChartRef = ref(null)

let equityChart = null
let drawdownChart = null
let profitDistributionChart = null
let signalTypeChart = null
let holdDaysChart = null
let monthlyReturnChart = null

// 策略类型文本
const strategyTypeText = computed(() => {
  const map = {
    'signal_based': '信号策略',
    'ma_cross': '均线交叉',
    'rsi': 'RSI策略',
    'macd': 'MACD策略'
  }
  return map[props.result.strategy_type] || props.result.strategy_type
})

// 收益率样式
const returnRateClass = computed(() => {
  return props.result.metrics.total_return_rate >= 0 ? 'positive' : 'negative'
})

// 胜率样式
const winRateClass = computed(() => {
  const winRate = props.result.metrics.win_rate * 100
  if (winRate >= 60) return 'positive'
  if (winRate >= 40) return 'neutral'
  return 'negative'
})

// 格式化函数
const formatPercentage = (value) => {
  if (value === null || value === undefined) return 'N/A'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

const formatNumber = (value, decimals = 0) => {
  if (value === null || value === undefined) return 'N/A'
  return value.toFixed(decimals)
}

// 信号类型
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

// 初始化资金曲线图
const initEquityChart = async () => {
  if (!equityChartRef.value) return
  
  const echarts = await loadECharts()
  if (!echarts) return
  
  if (equityChart) {
    equityChart.dispose()
  }
  
  equityChart = echarts.init(equityChartRef.value)
  const equityCurve = props.result.equity_curve || []
  
  if (equityCurve.length === 0) {
    equityChart.setOption({
      title: {
        text: '暂无资金曲线数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#999', fontSize: 14 }
      }
    })
    return
  }
  
  const dates = equityCurve.map(item => {
    const date = new Date(item.date)
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  })
  const capital = equityCurve.map(item => item.capital)
  const initialCapital = props.result.metrics.initial_capital
  
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const param = params[0]
        const returnRate = ((param.value - initialCapital) / initialCapital * 100).toFixed(2)
        return `${param.name}<br/>资金: ¥${param.value.toFixed(2)}<br/>收益率: ${returnRate >= 0 ? '+' : ''}${returnRate}%`
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
      name: '资金 (¥)',
      axisLabel: {
        formatter: '¥{value}'
      }
    },
    series: [
      {
        name: '资金曲线',
        type: 'line',
        smooth: true,
        data: capital,
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
            { yAxis: initialCapital, name: '初始资金', lineStyle: { color: '#909399', type: 'dashed' } }
          ]
        }
      }
    ]
  }
  
  equityChart.setOption(option)
  
  const resizeHandler = () => equityChart?.resize()
  window.addEventListener('resize', resizeHandler)
  
  // 保存清理函数
  if (!equityChart._resizeHandler) {
    equityChart._resizeHandler = resizeHandler
  }
}

// 初始化回撤曲线图
const initDrawdownChart = async () => {
  if (!drawdownChartRef.value) return
  
  const echarts = await loadECharts()
  if (!echarts) return
  
  if (drawdownChart) {
    drawdownChart.dispose()
  }
  
  drawdownChart = echarts.init(drawdownChartRef.value)
  const equityCurve = props.result.equity_curve || []
  
  if (equityCurve.length === 0) {
    drawdownChart.setOption({
      title: {
        text: '暂无回撤数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#999', fontSize: 14 }
      }
    })
    return
  }
  
  const dates = equityCurve.map(item => {
    const date = new Date(item.date)
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  })
  
  // 计算回撤
  let peak = equityCurve[0].capital
  const drawdowns = equityCurve.map(item => {
    if (item.capital > peak) {
      peak = item.capital
    }
    return ((item.capital - peak) / peak * 100).toFixed(2)
  })
  
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const param = params[0]
        return `${param.name}<br/>回撤: ${param.value}%`
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
      name: '回撤 (%)',
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: [
      {
        name: '回撤',
        type: 'line',
        smooth: true,
        data: drawdowns,
        lineStyle: {
          color: '#f56c6c',
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
              { offset: 0, color: 'rgba(245, 108, 108, 0.3)' },
              { offset: 1, color: 'rgba(245, 108, 108, 0.05)' }
            ]
          }
        }
      }
    ]
  }
  
  drawdownChart.setOption(option)
  
  const resizeHandler = () => drawdownChart?.resize()
  window.addEventListener('resize', resizeHandler)
  
  if (!drawdownChart._resizeHandler) {
    drawdownChart._resizeHandler = resizeHandler
  }
}

// 初始化交易盈亏分布图
const initProfitDistributionChart = async () => {
  if (!profitDistributionChartRef.value) return
  
  const echarts = await loadECharts()
  if (!echarts) return
  
  if (profitDistributionChart) {
    profitDistributionChart.dispose()
  }
  
  profitDistributionChart = echarts.init(profitDistributionChartRef.value)
  const trades = props.result.trades || []
  
  if (trades.length === 0) {
    profitDistributionChart.setOption({
      title: {
        text: '暂无交易数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#999', fontSize: 14 }
      }
    })
    return
  }
  
  // 计算盈亏分布
  const profits = trades.map(t => t.profit)
  const minProfit = Math.min(...profits)
  const maxProfit = Math.max(...profits)
  const binCount = 20
  const binSize = (maxProfit - minProfit) / binCount
  
  const bins = Array(binCount).fill(0)
  const binLabels = []
  
  for (let i = 0; i < binCount; i++) {
    binLabels.push((minProfit + i * binSize).toFixed(0))
  }
  
  profits.forEach(profit => {
    const binIndex = Math.min(Math.floor((profit - minProfit) / binSize), binCount - 1)
    bins[binIndex]++
  })
  
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const param = params[0]
        return `盈亏区间: ¥${param.name}<br/>交易次数: ${param.value}`
      }
    },
    grid: {
      left: '10%',
      right: '4%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: binLabels,
      axisLabel: {
        rotate: 45,
        fontSize: 10,
        formatter: (value) => `¥${value}`
      }
    },
    yAxis: {
      type: 'value',
      name: '交易次数'
    },
    series: [
      {
        name: '交易次数',
        type: 'bar',
        data: bins,
        itemStyle: {
          color: (params) => {
            const profit = parseFloat(binLabels[params.dataIndex])
            return profit >= 0 ? '#67c23a' : '#f56c6c'
          }
        }
      }
    ]
  }
  
  profitDistributionChart.setOption(option)
  
  const resizeHandler = () => profitDistributionChart?.resize()
  window.addEventListener('resize', resizeHandler)
  
  if (!profitDistributionChart._resizeHandler) {
    profitDistributionChart._resizeHandler = resizeHandler
  }
}

// 初始化信号类型分布图
const initSignalTypeChart = async () => {
  if (!signalTypeChartRef.value) return
  
  const echarts = await loadECharts()
  if (!echarts) return
  
  if (signalTypeChart) {
    signalTypeChart.dispose()
  }
  
  signalTypeChart = echarts.init(signalTypeChartRef.value)
  const trades = props.result.trades || []
  
  if (trades.length === 0) {
    signalTypeChart.setOption({
      title: {
        text: '暂无交易数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#999', fontSize: 14 }
      }
    })
    return
  }
  
  // 统计信号类型
  const signalCounts = {}
  trades.forEach(trade => {
    const type = trade.signal_type || 'unknown'
    signalCounts[type] = (signalCounts[type] || 0) + 1
  })
  
  const data = Object.entries(signalCounts).map(([type, count]) => ({
    name: signalTypeText(type),
    value: count
  }))
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 'middle'
    },
    series: [
      {
        name: '信号类型',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}: {c} ({d}%)'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        data: data,
        color: ['#67c23a', '#f56c6c', '#409eff']
      }
    ]
  }
  
  signalTypeChart.setOption(option)
  
  const resizeHandler = () => signalTypeChart?.resize()
  window.addEventListener('resize', resizeHandler)
  
  if (!signalTypeChart._resizeHandler) {
    signalTypeChart._resizeHandler = resizeHandler
  }
}

// 初始化持仓天数分布图
const initHoldDaysChart = async () => {
  if (!holdDaysChartRef.value) return
  
  const echarts = await loadECharts()
  if (!echarts) return
  
  if (holdDaysChart) {
    holdDaysChart.dispose()
  }
  
  holdDaysChart = echarts.init(holdDaysChartRef.value)
  const trades = props.result.trades || []
  
  if (trades.length === 0) {
    holdDaysChart.setOption({
      title: {
        text: '暂无交易数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#999', fontSize: 14 }
      }
    })
    return
  }
  
  // 统计持仓天数分布
  const holdDays = trades.map(t => t.hold_days || 0)
  const maxDays = Math.max(...holdDays)
  const binSize = Math.max(1, Math.ceil(maxDays / 10))
  const bins = {}
  
  holdDays.forEach(days => {
    const bin = Math.floor(days / binSize) * binSize
    bins[bin] = (bins[bin] || 0) + 1
  })
  
  const binLabels = Object.keys(bins).map(Number).sort((a, b) => a - b).map(d => `${d}-${d + binSize - 1}天`)
  const binValues = Object.keys(bins).map(Number).sort((a, b) => a - b).map(d => bins[d])
  
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const param = params[0]
        return `持仓天数: ${param.name}<br/>交易次数: ${param.value}`
      }
    },
    grid: {
      left: '10%',
      right: '4%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: binLabels,
      axisLabel: {
        rotate: 45,
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      name: '交易次数'
    },
    series: [
      {
        name: '交易次数',
        type: 'bar',
        data: binValues,
        itemStyle: {
          color: '#667eea'
        }
      }
    ]
  }
  
  holdDaysChart.setOption(option)
  
  const resizeHandler = () => holdDaysChart?.resize()
  window.addEventListener('resize', resizeHandler)
  
  if (!holdDaysChart._resizeHandler) {
    holdDaysChart._resizeHandler = resizeHandler
  }
}

// 初始化月度收益统计图
const initMonthlyReturnChart = async () => {
  if (!monthlyReturnChartRef.value) return
  
  const echarts = await loadECharts()
  if (!echarts) return
  
  if (monthlyReturnChart) {
    monthlyReturnChart.dispose()
  }
  
  monthlyReturnChart = echarts.init(monthlyReturnChartRef.value)
  const trades = props.result.trades || []
  
  if (trades.length === 0) {
    monthlyReturnChart.setOption({
      title: {
        text: '暂无交易数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#999', fontSize: 14 }
      }
    })
    return
  }
  
  // 按月份统计收益
  const monthlyReturns = {}
  trades.forEach(trade => {
    if (trade.sell_date) {
      const date = new Date(trade.sell_date.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3'))
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
      monthlyReturns[monthKey] = (monthlyReturns[monthKey] || 0) + (trade.profit || 0)
    }
  })
  
  const months = Object.keys(monthlyReturns).sort()
  const returns = months.map(m => monthlyReturns[m])
  
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const param = params[0]
        return `${param.name}<br/>收益: ${param.value >= 0 ? '+' : ''}¥${param.value.toFixed(2)}`
      }
    },
    grid: {
      left: '10%',
      right: '4%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: months,
      axisLabel: {
        rotate: 45,
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      name: '收益 (¥)',
      axisLabel: {
        formatter: '¥{value}'
      }
    },
    series: [
      {
        name: '月度收益',
        type: 'bar',
        data: returns,
        itemStyle: {
          color: (params) => {
            return params.value >= 0 ? '#67c23a' : '#f56c6c'
          }
        }
      }
    ]
  }
  
  monthlyReturnChart.setOption(option)
  
  const resizeHandler = () => monthlyReturnChart?.resize()
  window.addEventListener('resize', resizeHandler)
  
  if (!monthlyReturnChart._resizeHandler) {
    monthlyReturnChart._resizeHandler = resizeHandler
  }
}

// 监听标签页切换
watch(activeTab, async (newTab) => {
  await nextTick()
  if (newTab === 'equity') {
    initEquityChart()
    initDrawdownChart()
  } else if (newTab === 'analysis') {
    initProfitDistributionChart()
    initSignalTypeChart()
    initHoldDaysChart()
    initMonthlyReturnChart()
  }
})

onMounted(async () => {
  await nextTick()
  if (activeTab.value === 'equity') {
    initEquityChart()
    initDrawdownChart()
  } else if (activeTab.value === 'analysis') {
    initProfitDistributionChart()
    initSignalTypeChart()
    initHoldDaysChart()
    initMonthlyReturnChart()
  }
})

onUnmounted(() => {
  // 移除窗口resize监听器并清理所有图表实例
  if (equityChart?._resizeHandler) {
    window.removeEventListener('resize', equityChart._resizeHandler)
    equityChart.dispose()
  }
  if (drawdownChart?._resizeHandler) {
    window.removeEventListener('resize', drawdownChart._resizeHandler)
    drawdownChart.dispose()
  }
  if (profitDistributionChart?._resizeHandler) {
    window.removeEventListener('resize', profitDistributionChart._resizeHandler)
    profitDistributionChart.dispose()
  }
  if (signalTypeChart?._resizeHandler) {
    window.removeEventListener('resize', signalTypeChart._resizeHandler)
    signalTypeChart.dispose()
  }
  if (holdDaysChart?._resizeHandler) {
    window.removeEventListener('resize', holdDaysChart._resizeHandler)
    holdDaysChart.dispose()
  }
  if (monthlyReturnChart?._resizeHandler) {
    window.removeEventListener('resize', monthlyReturnChart._resizeHandler)
    monthlyReturnChart.dispose()
  }
})
</script>

<style scoped>
.backtest-result {
  padding: 20px;
}

.backtest-header {
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

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  text-align: center;
  border-radius: 12px;
  transition: all 0.3s;
}

.metric-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.highlight-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.highlight-card .metric-label {
  color: rgba(255, 255, 255, 0.9);
}

.highlight-card .metric-value {
  color: #ffffff;
}

.highlight-card .metric-sub {
  color: rgba(255, 255, 255, 0.8);
}

.metric-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #2d3748;
  margin-bottom: 8px;
}

.metric-value.positive {
  color: #67c23a;
}

.metric-value.negative {
  color: #f56c6c;
}

.metric-value.neutral {
  color: #e6a23c;
}

.metric-sub {
  font-size: 12px;
  color: #999;
}

.detailed-metrics {
  margin-top: 16px;
}

.metrics-title {
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.detailed-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 6px;
}

.item-label {
  color: #666;
  font-size: 13px;
}

.item-value {
  font-weight: 600;
  font-size: 14px;
  color: #2d3748;
}

.item-value.positive {
  color: #67c23a;
}

.item-value.negative {
  color: #f56c6c;
}

.chart-card {
  margin-top: 16px;
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

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 20px;
}

.analysis-section {
  margin-top: 16px;
}

@media (max-width: 1200px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}

.trades-section {
  margin-top: 16px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
}

.empty-state .el-icon {
  margin-bottom: 16px;
}

.positive {
  color: #67c23a;
}

.negative {
  color: #f56c6c;
}
</style>

