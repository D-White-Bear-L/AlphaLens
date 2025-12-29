<template>
  <div class="stock-recommendation-result">
    <!-- 顶部信息 -->
    <div class="result-header">
      <div class="badges-container">
        <div class="period-badge">
          <el-icon><Calendar /></el-icon>
          <span>{{ result.analysis_period }}</span>
        </div>
        <div class="analyzed-badge">
          <el-icon><DataAnalysis /></el-icon>
          <span>共分析 {{ result.total_analyzed }} 只股票</span>
        </div>
        <div class="recommendations-badge">
          <el-icon><Star /></el-icon>
          <span>推荐 {{ result.recommendations.length }} 只</span>
        </div>
      </div>
    </div>

    <!-- 对比分析摘要 -->
    <div class="comparison-summary">
      <h3>
        <el-icon><InfoFilled /></el-icon>
        综合对比分析
      </h3>
      <div class="summary-content">{{ result.comparison_summary }}</div>
    </div>

    <!-- 推荐列表 -->
    <div class="recommendations-section">
      <h3>
        <el-icon><Star /></el-icon>
        股票推荐排名
      </h3>
      
      <div v-if="result.recommendations.length === 0" class="empty-state">
        <div class="empty-icon">
          <el-icon :size="48"><Box /></el-icon>
        </div>
        <p>未找到符合条件的推荐股票</p>
      </div>
      
      <div v-else class="recommendations-list">
        <el-card 
          v-for="rec in result.recommendations" 
          :key="rec.rank"
          class="recommendation-card"
          :class="`rank-${rec.rank}`"
        >
          <!-- 排名徽章 -->
          <div class="rank-badge" :class="getRankClass(rec.rank)">
            <span class="rank-number">{{ rec.rank }}</span>
            <span class="rank-label">名</span>
          </div>
          
          <!-- 股票基本信息 -->
          <div class="stock-header">
            <div class="stock-title">
              <h4>{{ rec.stock_code }}{{ rec.stock_name ? ` - ${rec.stock_name}` : '' }}</h4>
              <div class="stock-meta">
                <el-tag :type="getRiskTagType(rec.risk_level)" size="small">
                  {{ getRiskText(rec.risk_level) }}
                </el-tag>
                <el-tag :type="getTrendTagType(rec.trend_direction)" size="small">
                  {{ getTrendText(rec.trend_direction) }}
                </el-tag>
              </div>
            </div>
            <div class="score-section">
              <div class="score-label">推荐分数</div>
              <div class="score-value" :class="getScoreClass(rec.recommendation_score)">
                {{ (rec.recommendation_score * 100).toFixed(1) }}
              </div>
              <el-progress 
                :percentage="rec.recommendation_score * 100" 
                :color="getScoreColor(rec.recommendation_score)"
                :stroke-width="8"
                :show-text="false"
              />
            </div>
          </div>
          
          <!-- 价格信息 -->
          <div class="price-info">
            <div class="price-item">
              <span class="price-label">当前价格</span>
              <span class="price-value">{{ formatPrice(rec.current_price) }}</span>
            </div>
            <div class="price-item" :class="rec.price_change_pct >= 0 ? 'positive' : 'negative'">
              <span class="price-label">涨跌幅</span>
              <span class="price-value">
                {{ rec.price_change_pct >= 0 ? '+' : '' }}{{ rec.price_change_pct.toFixed(2) }}%
              </span>
            </div>
          </div>
          
          <!-- 推荐理由 -->
          <div class="recommendation-reason">
            <h5>
              <el-icon><Edit /></el-icon>
              推荐理由
            </h5>
            <div class="reason-text">{{ rec.recommendation_reason }}</div>
          </div>
          
          <!-- 关键亮点 -->
          <div v-if="rec.key_highlights && rec.key_highlights.length > 0" class="key-highlights">
            <h5>
              <el-icon><Star /></el-icon>
              关键亮点
            </h5>
            <ul class="highlights-list">
              <li v-for="(highlight, idx) in rec.key_highlights" :key="idx">
                {{ highlight }}
              </li>
            </ul>
          </div>
          
          <!-- 查看详细分析 -->
          <div v-if="rec.analysis_summary" class="analysis-link">
            <el-button 
              type="primary" 
              text 
              size="small"
              @click="showDetailAnalysis(rec)"
            >
              <el-icon><DataAnalysis /></el-icon>
              查看详细分析
            </el-button>
          </div>
        </el-card>
      </div>
    </div>
    
    <!-- 详细分析对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="`${selectedStock?.stock_code}${selectedStock?.stock_name ? ` - ${selectedStock.stock_name}` : ''} 详细分析`"
      width="60%"
      :close-on-click-modal="false"
    >
      <FinancialResult v-if="selectedStock?.analysis_summary" :result="selectedStock.analysis_summary" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { 
  Calendar, DataAnalysis, Star, InfoFilled, 
  Box, Edit
} from '@element-plus/icons-vue'
import FinancialResult from './FinancialResult.vue'

const props = defineProps({
  result: {
    type: Object,
    required: true
  }
})

const detailDialogVisible = ref(false)
const selectedStock = ref(null)

// 格式化价格
const formatPrice = (value) => {
  if (value === null || value === undefined) return 'N/A'
  return value.toFixed(2)
}

// 排名样式
const getRankClass = (rank) => {
  if (rank === 1) return 'rank-gold'
  if (rank === 2) return 'rank-silver'
  if (rank === 3) return 'rank-bronze'
  return 'rank-normal'
}

// 风险等级
const getRiskText = (level) => {
  const map = {
    'low': '低风险',
    'medium': '中风险',
    'high': '高风险'
  }
  return map[level] || level
}

const getRiskTagType = (level) => {
  const map = {
    'low': 'success',
    'medium': 'warning',
    'high': 'danger'
  }
  return map[level] || 'info'
}

// 趋势方向
const getTrendText = (trend) => {
  const map = {
    'up': '上涨',
    'down': '下跌',
    'sideways': '横盘'
  }
  return map[trend] || trend
}

const getTrendTagType = (trend) => {
  const map = {
    'up': 'success',
    'down': 'danger',
    'sideways': 'info'
  }
  return map[trend] || 'info'
}

// 分数样式
const getScoreClass = (score) => {
  if (score >= 0.8) return 'score-high'
  if (score >= 0.6) return 'score-medium'
  return 'score-low'
}

const getScoreColor = (score) => {
  if (score >= 0.8) return '#67c23a'
  if (score >= 0.6) return '#e6a23c'
  return '#f56c6c'
}

// 显示详细分析
const showDetailAnalysis = (stock) => {
  selectedStock.value = stock
  detailDialogVisible.value = true
}
</script>

<style scoped>
.stock-recommendation-result {
  padding: 20px;
}

.result-header {
  margin-bottom: 24px;
}

.badges-container {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.period-badge,
.analyzed-badge,
.recommendations-badge {
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
  background: #f5f5f5;
  color: #666;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.comparison-summary {
  margin-bottom: 32px;
  padding: 20px;
  background: #f9f9f9;
  border-radius: 12px;
  border-left: 4px solid #667eea;
}

.comparison-summary h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-content {
  line-height: 1.8;
  color: #2d3748;
  white-space: pre-wrap;
}

.recommendations-section h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
  color: #2d3748;
  display: flex;
  align-items: center;
  gap: 8px;
}

.recommendations-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.recommendation-card {
  position: relative;
  padding: 20px;
  border-left: 4px solid #ddd;
  transition: all 0.3s;
}

.recommendation-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.recommendation-card.rank-1 {
  border-left-color: #ffd700;
  background: linear-gradient(to right, #fffef0 0%, #ffffff 10%);
}

.recommendation-card.rank-2 {
  border-left-color: #c0c0c0;
  background: linear-gradient(to right, #f8f8f8 0%, #ffffff 10%);
}

.recommendation-card.rank-3 {
  border-left-color: #cd7f32;
  background: linear-gradient(to right, #faf5f0 0%, #ffffff 10%);
}

.rank-badge {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: white;
}

.rank-badge.rank-gold {
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  box-shadow: 0 4px 12px rgba(255, 215, 0, 0.3);
}

.rank-badge.rank-silver {
  background: linear-gradient(135deg, #c0c0c0 0%, #e8e8e8 100%);
  box-shadow: 0 4px 12px rgba(192, 192, 192, 0.3);
}

.rank-badge.rank-bronze {
  background: linear-gradient(135deg, #cd7f32 0%, #e6a85c 100%);
  box-shadow: 0 4px 12px rgba(205, 127, 50, 0.3);
}

.rank-badge.rank-normal {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.rank-number {
  font-size: 24px;
  line-height: 1;
}

.rank-label {
  font-size: 12px;
  margin-top: 2px;
}

.stock-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  padding-right: 80px;
}

.stock-title h4 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #2d3748;
}

.stock-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.score-section {
  text-align: right;
  min-width: 120px;
}

.score-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.score-value {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}

.score-value.score-high {
  color: #67c23a;
}

.score-value.score-medium {
  color: #e6a23c;
}

.score-value.score-low {
  color: #f56c6c;
}

.price-info {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 8px;
}

.price-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.price-label {
  font-size: 12px;
  color: #666;
}

.price-value {
  font-size: 18px;
  font-weight: 600;
  color: #2d3748;
}

.price-item.positive .price-value {
  color: #67c23a;
}

.price-item.negative .price-value {
  color: #f56c6c;
}

.recommendation-reason {
  margin-bottom: 16px;
}

.recommendation-reason h5 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
  color: #2d3748;
  display: flex;
  align-items: center;
  gap: 6px;
}

.reason-text {
  line-height: 1.8;
  color: #2d3748;
  white-space: pre-wrap;
}

.key-highlights {
  margin-bottom: 16px;
}

.key-highlights h5 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
  color: #2d3748;
  display: flex;
  align-items: center;
  gap: 6px;
}

.highlights-list {
  margin: 0;
  padding-left: 20px;
  color: #2d3748;
}

.highlights-list li {
  margin-bottom: 6px;
  line-height: 1.6;
}

.analysis-link {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
}

.empty-icon {
  margin-bottom: 16px;
}
</style>

