<template>
  <div class="prediction-result">
    <!-- 预测信息头部 -->
    <div class="prediction-header">
      <div class="header-info">
        <h3 class="stock-title">
          <el-icon><TrendCharts /></el-icon>
          {{ result.stock_code }}{{ result.stock_name ? ` - ${result.stock_name}` : '' }}
        </h3>
        <div class="info-row">
          <span>训练期间: {{ result.training_period }}</span>
          <span>模型类型: {{ modelTypeText }}</span>
          <span v-if="result.model_accuracy !== null && result.model_accuracy !== undefined">
            模型准确度: {{ (result.model_accuracy * 100).toFixed(2) }}%
          </span>
        </div>
      </div>
    </div>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab" class="result-tabs">
      <!-- 预测概览 -->
      <el-tab-pane name="overview">
        <template #label>
          <el-icon><DataAnalysis /></el-icon>
          <span>预测概览</span>
        </template>
        <div class="overview-section">
          <!-- 核心指标卡片 -->
          <div class="metrics-grid">
            <el-card class="metric-card highlight-card">
              <div class="metric-label">预测天数</div>
              <div class="metric-value">{{ result.prediction_days }} 天</div>
              <div class="metric-sub">
                预测时间: {{ formatTimestamp(result.prediction_timestamp) }}
              </div>
            </el-card>
            
            <el-card class="metric-card" v-if="result.model_accuracy !== null && result.model_accuracy !== undefined">
              <div class="metric-label">模型准确度</div>
              <div class="metric-value" :class="accuracyClass">
                {{ (result.model_accuracy * 100).toFixed(2) }}%
              </div>
              <div class="metric-sub">
                基于验证集 R² 分数
              </div>
            </el-card>
            
            <el-card class="metric-card" v-if="predictions.length > 0">
              <div class="metric-label">预测价格范围</div>
              <div class="metric-value">
                ¥{{ formatNumber(minPrice) }} - ¥{{ formatNumber(maxPrice) }}
              </div>
              <div class="metric-sub">
                当前价格: ¥{{ formatNumber(currentPrice) }}
              </div>
            </el-card>
            
            <el-card class="metric-card" v-if="predictions.length > 0">
              <div class="metric-label">预期变化</div>
              <div class="metric-value" :class="priceChangeClass">
                {{ formatPercentage(priceChangePercent) }}
              </div>
              <div class="metric-sub">
                {{ priceChangePercent >= 0 ? '上涨' : '下跌' }} ¥{{ formatNumber(Math.abs(priceChange)) }}
              </div>
            </el-card>
          </div>
          
          <!-- 预测点列表 -->
          <el-card class="predictions-card" v-if="predictions.length > 0">
            <div class="card-title">
              <el-icon><List /></el-icon>
              预测详情
            </div>
            <el-table 
              :data="predictions" 
              stripe
              style="width: 100%"
            >
              <el-table-column prop="date" label="日期" width="120" />
              <el-table-column prop="predicted_price" label="预测价格" width="120">
                <template #default="{ row }">
                  ¥{{ formatNumber(row.predicted_price, 2) }}
                </template>
              </el-table-column>
              <el-table-column label="置信区间" width="200">
                <template #default="{ row }">
                  <span v-if="row.confidence_interval_lower && row.confidence_interval_upper">
                    ¥{{ formatNumber(row.confidence_interval_lower, 2) }} - 
                    ¥{{ formatNumber(row.confidence_interval_upper, 2) }}
                  </span>
                  <span v-else>N/A</span>
                </template>
              </el-table-column>
              <el-table-column prop="prediction_confidence" label="置信度" width="120">
                <template #default="{ row }">
                  <el-progress 
                    :percentage="row.prediction_confidence * 100" 
                    :color="getConfidenceColor(row.prediction_confidence)"
                    :stroke-width="8"
                    :format="(val) => val.toFixed(0) + '%'"
                  />
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 预测走势图 -->
      <el-tab-pane name="chart">
        <template #label>
          <el-icon><TrendCharts /></el-icon>
          <span>预测走势</span>
        </template>
        <div class="chart-section">
          <el-card class="chart-card">
            <div class="chart-title">价格预测走势图</div>
            <div ref="predictionChartRef" class="chart-container"></div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 特征重要性 -->
      <el-tab-pane name="features" v-if="result.feature_importance">
        <template #label>
          <el-icon><Operation /></el-icon>
          <span>特征重要性</span>
        </template>
        <div class="features-section">
          <el-card class="chart-card">
            <div class="chart-title">特征重要性分析</div>
            <div ref="featureImportanceChartRef" class="chart-container"></div>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { DataAnalysis, TrendCharts, Operation, List } from '@element-plus/icons-vue'

const props = defineProps({
  result: {
    type: Object,
    required: true
  }
})

const activeTab = ref('overview')
const predictionChartRef = ref(null)
const featureImportanceChartRef = ref(null)

let predictionChart = null
let featureImportanceChart = null

// 模型类型文本
const modelTypeText = computed(() => {
  const map = {
    'linear': '线性回归',
    'ridge': 'Ridge回归',
    'lasso': 'Lasso回归',
    'random_forest': '随机森林',
    'gradient_boosting': '梯度提升',
    'ensemble': '集成模型'
  }
  return map[props.result.model_type] || props.result.model_type
})

// 预测点列表
const predictions = computed(() => props.result.predictions || [])

// 价格相关计算
const currentPrice = computed(() => {
  if (predictions.value.length === 0) return 0
  return predictions.value[0].predicted_price
})

const minPrice = computed(() => {
  if (predictions.value.length === 0) return 0
  return Math.min(...predictions.value.map(p => p.predicted_price))
})

const maxPrice = computed(() => {
  if (predictions.value.length === 0) return 0
  return Math.max(...predictions.value.map(p => p.predicted_price))
})

const priceChange = computed(() => {
  if (predictions.value.length === 0) return 0
  const firstPrice = predictions.value[0].predicted_price
  const lastPrice = predictions.value[predictions.value.length - 1].predicted_price
  return lastPrice - firstPrice
})

const priceChangePercent = computed(() => {
  if (predictions.value.length === 0 || currentPrice.value === 0) return 0
  return (priceChange.value / currentPrice.value) * 100
})

const priceChangeClass = computed(() => {
  return priceChangePercent.value >= 0 ? 'positive' : 'negative'
})

const accuracyClass = computed(() => {
  const accuracy = props.result.model_accuracy || 0
  if (accuracy >= 0.7) return 'positive'
  if (accuracy >= 0.4) return 'neutral'
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

const formatTimestamp = (timestamp) => {
  if (!timestamp) return 'N/A'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN')
}

const getConfidenceColor = (confidence) => {
  if (confidence >= 0.7) return '#67c23a'
  if (confidence >= 0.4) return '#e6a23c'
  return '#f56c6c'
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

// 初始化预测走势图
const initPredictionChart = async () => {
  if (!predictionChartRef.value) return
  
  const echarts = await loadECharts()
  if (!echarts) return
  
  if (predictionChart) {
    predictionChart.dispose()
  }
  
  predictionChart = echarts.init(predictionChartRef.value)
  const predictions = props.result.predictions || []
  
  if (predictions.length === 0) {
    predictionChart.setOption({
      title: {
        text: '暂无预测数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#999', fontSize: 14 }
      }
    })
    return
  }
  
  const dates = predictions.map(p => {
    const date = new Date(p.date)
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  })
  const prices = predictions.map(p => p.predicted_price)
  const lowerBounds = predictions.map(p => p.confidence_interval_lower || p.predicted_price)
  const upperBounds = predictions.map(p => p.confidence_interval_upper || p.predicted_price)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const param = params[0]
        const date = param.name
        const price = param.value.toFixed(2)
        const prediction = predictions.find(p => {
          const pDate = new Date(p.date)
          return pDate.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }) === date
        })
        let result = `${date}<br/>预测价格: ¥${price}`
        if (prediction && prediction.confidence_interval_lower && prediction.confidence_interval_upper) {
          result += `<br/>置信区间: ¥${prediction.confidence_interval_lower.toFixed(2)} - ¥${prediction.confidence_interval_upper.toFixed(2)}`
          result += `<br/>置信度: ${(prediction.prediction_confidence * 100).toFixed(0)}%`
        }
        return result
      }
    },
    legend: {
      data: ['预测价格', '置信区间'],
      top: 10
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
        name: '预测价格',
        type: 'line',
        smooth: true,
        data: prices,
        lineStyle: {
          color: '#667eea',
          width: 3
        },
        itemStyle: {
          color: '#667eea'
        },
        markPoint: {
          data: [
            { type: 'max', name: '最高价' },
            { type: 'min', name: '最低价' }
          ]
        }
      },
      {
        name: '置信区间',
        type: 'line',
        data: predictions.map(p => p.confidence_interval_upper || p.predicted_price),
        lineStyle: {
          color: '#95a5a6',
          type: 'dashed',
          width: 1
        },
        itemStyle: {
          color: 'transparent'
        },
        symbol: 'none'
      },
      {
        name: '置信区间',
        type: 'line',
        data: predictions.map(p => p.confidence_interval_lower || p.predicted_price),
        lineStyle: {
          color: '#95a5a6',
          type: 'dashed',
          width: 1
        },
        itemStyle: {
          color: 'transparent'
        },
        symbol: 'none',
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(102, 126, 234, 0.2)' },
              { offset: 1, color: 'rgba(102, 126, 234, 0.05)' }
            ]
          }
        }
      }
    ]
  }
  
  predictionChart.setOption(option)
  
  const resizeHandler = () => predictionChart?.resize()
  window.addEventListener('resize', resizeHandler)
  
  if (!predictionChart._resizeHandler) {
    predictionChart._resizeHandler = resizeHandler
  }
}

// 初始化特征重要性图
const initFeatureImportanceChart = async () => {
  if (!featureImportanceChartRef.value) return
  
  const echarts = await loadECharts()
  if (!echarts) return
  
  if (featureImportanceChart) {
    featureImportanceChart.dispose()
  }
  
  featureImportanceChart = echarts.init(featureImportanceChartRef.value)
  const featureImportance = props.result.feature_importance || {}
  
  if (Object.keys(featureImportance).length === 0) {
    featureImportanceChart.setOption({
      title: {
        text: '暂无特征重要性数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#999', fontSize: 14 }
      }
    })
    return
  }
  
  // 按重要性排序
  const sortedFeatures = Object.entries(featureImportance)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15) // 只显示前15个最重要的特征
  
  const featureNames = sortedFeatures.map(([name]) => name)
  const importanceValues = sortedFeatures.map(([, value]) => value)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params) => {
        const param = params[0]
        return `${param.name}<br/>重要性: ${(param.value * 100).toFixed(2)}%`
      }
    },
    grid: {
      left: '15%',
      right: '4%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      name: '重要性',
      axisLabel: {
        formatter: '{value}'
      }
    },
    yAxis: {
      type: 'category',
      data: featureNames,
      axisLabel: {
        fontSize: 10
      }
    },
    series: [
      {
        name: '特征重要性',
        type: 'bar',
        data: importanceValues,
        itemStyle: {
          color: '#667eea'
        }
      }
    ]
  }
  
  featureImportanceChart.setOption(option)
  
  const resizeHandler = () => featureImportanceChart?.resize()
  window.addEventListener('resize', resizeHandler)
  
  if (!featureImportanceChart._resizeHandler) {
    featureImportanceChart._resizeHandler = resizeHandler
  }
}

// 监听标签页切换
watch(activeTab, async (newTab) => {
  await nextTick()
  if (newTab === 'chart') {
    initPredictionChart()
  } else if (newTab === 'features') {
    initFeatureImportanceChart()
  }
})

onMounted(async () => {
  await nextTick()
  if (activeTab.value === 'chart') {
    initPredictionChart()
  } else if (activeTab.value === 'features') {
    initFeatureImportanceChart()
  }
})

onUnmounted(() => {
  if (predictionChart?._resizeHandler) {
    window.removeEventListener('resize', predictionChart._resizeHandler)
    predictionChart.dispose()
  }
  if (featureImportanceChart?._resizeHandler) {
    window.removeEventListener('resize', featureImportanceChart._resizeHandler)
    featureImportanceChart.dispose()
  }
})
</script>

<style scoped>
.prediction-result {
  padding: 20px;
}

.prediction-header {
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
  flex-wrap: wrap;
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

.predictions-card {
  margin-top: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
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

.positive {
  color: #67c23a;
}

.negative {
  color: #f56c6c;
}
</style>

