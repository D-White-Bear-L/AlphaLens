<template>
  <div class="chat-view" ref="chatView">
    <!-- 有消息时显示聊天界面 -->
    <template v-if="messages.length > 0">
      <!-- 聊天消息区域 -->
      <div class="chat-messages" ref="messagesContainer">
        <div v-for="(message, index) in messages" :key="index" 
             :class="['message', message.role]">
          <div class="message-content">
            <div v-if="message.role === 'user'" class="message-bubble user-bubble">
              {{ message.content }}
            </div>
            <div v-else-if="message.role === 'assistant'" class="message-bubble assistant-bubble">
              <div v-if="message.type === 'trace'">
                <!-- 新闻溯源结果展示 -->
                <NewsTraceResult :result="message.data" />
              </div>
              <div v-else-if="message.type === 'financial'">
                <!-- 金融分析结果展示 -->
                <FinancialResult :result="message.data" />
              </div>
              <div v-else-if="message.type === 'stock_recommendation'">
                <!-- 股票推荐结果展示 -->
                <StockRecommendationResult :result="message.data" />
              </div>
              <div v-else-if="message.type === 'backtest'">
                <!-- 策略回测结果展示 -->
                <BacktestResult :result="message.data" />
              </div>
              <div v-else-if="message.type === 'prediction'">
                <!-- 股票预测结果展示 -->
                <PredictionResult :result="message.data" />
              </div>
              <div v-else-if="message.type === 'progress'" class="progress-message">
                <div class="progress-header">
                  <div class="progress-text">{{ message.content }}</div>
                  <el-button 
                    v-if="message.taskId && loading"
                    type="danger" 
                    size="small" 
                    text
                    @click="cancelTask(message.taskId)"
                    :icon="Close"
                    class="cancel-btn"
                  >
                    取消
                  </el-button>
                </div>
                <el-progress 
                  :percentage="(message.progress || 0) * 100" 
                  :status="message.progress === 1 ? 'success' : (message.cancelled ? 'exception' : undefined)"
                  :stroke-width="8"
                  :format="formatProgress"
                  style="margin-top: 8px;"
                />
              </div>
              <div v-else>
                {{ message.content }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="chat-input-area">
        <!-- 设置面板折叠按钮 -->
        <div 
          v-if="selectedAgent?.id === 'news_trace' || selectedAgent?.id === 'finance_quant'" 
          class="settings-toggle"
          @click="settingsCollapsed = !settingsCollapsed"
        >
          <el-icon><component :is="settingsCollapsed ? ArrowDown : ArrowUp" /></el-icon>
          <span>{{ settingsCollapsed ? '展开设置' : '收起设置' }}</span>
        </div>
        
        <!-- 深度设置（仅新闻溯源Agent显示） -->
        <transition name="settings-slide">
          <div v-if="selectedAgent?.id === 'news_trace' && !settingsCollapsed" class="depth-settings">
            <div class="depth-label">
              <el-icon><DataAnalysis /></el-icon>
              <span>溯源深度：</span>
            </div>
            <el-radio-group v-model="traceDepth" size="small" class="depth-selector">
              <el-radio-button :label="1">浅层 (快速)</el-radio-button>
              <el-radio-button :label="2">中等 (推荐)</el-radio-button>
              <el-radio-button :label="3">深层 (详细)</el-radio-button>
              <el-radio-button :label="4">极深 (全面)</el-radio-button>
            </el-radio-group>
            <div class="depth-hint">
              <el-icon><InfoFilled /></el-icon>
              <span>{{ getDepthHint(traceDepth) }}</span>
            </div>
          </div>
        </transition>
        <!-- 金融分析输入表单（仅金融量化Agent显示） -->
        <transition name="settings-slide">
          <div v-if="selectedAgent?.id === 'finance_quant' && !settingsCollapsed" class="financial-settings">
          <!-- 模式切换 -->
          <div class="mode-selector">
            <el-radio-group v-model="financialMode" size="small" @change="onFinancialModeChange">
              <el-radio-button label="analysis">
                <el-icon><DataAnalysis /></el-icon>
                <span style="margin-left: 4px;">单股票分析</span>
              </el-radio-button>
              <el-radio-button label="recommendation">
                <el-icon><Star /></el-icon>
                <span style="margin-left: 4px;">股票推荐</span>
              </el-radio-button>
              <el-radio-button label="backtest">
                <el-icon><TrendCharts /></el-icon>
                <span style="margin-left: 4px;">策略回测</span>
              </el-radio-button>
              <el-radio-button label="prediction">
                <el-icon><TrendCharts /></el-icon>
                <span style="margin-left: 4px;">股票预测</span>
              </el-radio-button>
            </el-radio-group>
          </div>
          
          <!-- 单股票分析表单 -->
          <div v-if="financialMode === 'analysis'" class="financial-form">
            <el-form :inline="true" size="small">
              <el-form-item label="股票代码">
                <el-input 
                  v-model="stockCode" 
                  placeholder="如: 000001"
                  style="width: 120px"
                  :disabled="loading"
                />
              </el-form-item>
              <el-form-item label="开始日期">
                <el-date-picker
                  v-model="startDate"
                  type="date"
                  placeholder="选择日期"
                  format="YYYYMMDD"
                  value-format="YYYYMMDD"
                  style="width: 150px"
                  :disabled="loading"
                />
              </el-form-item>
              <el-form-item label="结束日期">
                <el-date-picker
                  v-model="endDate"
                  type="date"
                  placeholder="选择日期"
                  format="YYYYMMDD"
                  value-format="YYYYMMDD"
                  style="width: 150px"
                  :disabled="loading"
                />
              </el-form-item>
            </el-form>
          </div>
          
          <!-- 股票推荐表单 -->
          <div v-else-if="financialMode === 'recommendation'" class="financial-form recommendation-form">
            <el-form :inline="true" size="small">
              <el-form-item label="股票代码">
                <el-input 
                  v-model="recommendationStockCodes" 
                  placeholder="留空自动获取热门股票，或用逗号分隔，如: 000001,000002"
                  style="width: 300px"
                  :disabled="loading"
                />
                <div class="form-hint">留空则自动获取热门股票</div>
              </el-form-item>
              <el-form-item label="开始日期">
                <el-date-picker
                  v-model="startDate"
                  type="date"
                  placeholder="选择日期"
                  format="YYYYMMDD"
                  value-format="YYYYMMDD"
                  style="width: 150px"
                  :disabled="loading"
                />
              </el-form-item>
              <el-form-item label="结束日期">
                <el-date-picker
                  v-model="endDate"
                  type="date"
                  placeholder="选择日期"
                  format="YYYYMMDD"
                  value-format="YYYYMMDD"
                  style="width: 150px"
                  :disabled="loading"
                />
              </el-form-item>
              <el-form-item label="最大推荐数">
                <el-input-number
                  v-model="maxStocks"
                  :min="1"
                  :max="50"
                  :step="1"
                  style="width: 100px"
                  :disabled="loading"
                />
              </el-form-item>
              <el-form-item label="最低分数">
                <el-input-number
                  v-model="minRecommendationScore"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  :precision="1"
                  style="width: 100px"
                  :disabled="loading"
                />
              </el-form-item>
              <el-form-item label="行业筛选">
                <el-input 
                  v-model="focusSector" 
                  placeholder="如: 科技、金融、消费"
                  style="width: 120px"
                  :disabled="loading"
                />
                <div class="form-hint">可选，留空不筛选</div>
              </el-form-item>
            </el-form>
          </div>
          
          <!-- 策略回测表单 -->
          <div v-else-if="financialMode === 'backtest'" class="backtest-form-wrapper">
            <BacktestForm 
              :loading="loading"
              @update:formData="handleBacktestFormUpdate"
              ref="backtestFormRef"
            />
          </div>
          
          <!-- 股票预测表单 -->
          <div v-else-if="financialMode === 'prediction'" class="prediction-form-wrapper">
            <PredictionForm 
              :loading="loading"
              @update:formData="handlePredictionFormUpdate"
              ref="predictionFormRef"
            />
          </div>
          </div>
        </transition>
        <div class="input-wrapper">
          <el-input
            v-if="selectedAgent?.id !== 'finance_quant'"
            v-model="inputMessage"
            type="textarea"
            :rows="1"
            placeholder="输入消息..."
            @keydown.enter.exact.prevent="sendMessage"
            @keydown.shift.enter.exact="inputMessage += '\n'"
            :disabled="loading"
            class="chat-input"
            resize="none"
          />
            <div v-else class="financial-input-hint">
              <el-icon><InfoFilled /></el-icon>
              <span v-if="financialMode === 'analysis'">请填写股票代码和日期范围，然后点击发送开始分析</span>
              <span v-else-if="financialMode === 'recommendation'">请填写日期范围，然后点击发送开始推荐</span>
              <span v-else-if="financialMode === 'backtest'">请填写回测参数，然后点击发送开始回测</span>
            </div>
          <el-button 
            :type="loading && currentTaskId ? 'danger' : 'primary'"
            @click="handleSendOrCancel"
            :disabled="loading && currentTaskId ? false : (!canSendMessage && !loading)"
            class="send-btn"
          >
            <template v-if="loading && currentTaskId">
              <el-icon><VideoPause /></el-icon>
              <span style="margin-left: 4px;">暂停</span>
            </template>
            <template v-else-if="loading">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span style="margin-left: 4px;">处理中</span>
            </template>
            <template v-else>发送</template>
          </el-button>
        </div>
      </div>
    </template>

    <!-- 初始状态：欢迎界面 -->
    <template v-else>
      <div class="welcome-container">
        <div class="welcome-content">
          <h1 class="welcome-title">您今天在想什么?</h1>
          
          <!-- Agent 选择卡片 -->
          <div class="agent-cards">
            <div 
              v-for="agent in agents" 
              :key="agent.id"
              class="agent-card"
              :class="{ 'selected': selectedAgent?.id === agent.id, 'disabled': agent.disabled }"
              @click="selectAgent(agent)"
            >
              <div class="agent-icon">
                <el-icon>
                  <component :is="agent.iconComponent || agent.icon" />
                </el-icon>
              </div>
              <div class="agent-name">{{ agent.name }}</div>
              <div class="agent-desc">{{ agent.description }}</div>
            </div>
          </div>
        </div>

        <!-- 底部输入框 -->
        <div class="welcome-input-area">
          <!-- 设置面板折叠按钮 -->
          <div 
            v-if="selectedAgent?.id === 'news_trace' || selectedAgent?.id === 'finance_quant'" 
            class="settings-toggle"
            @click="settingsCollapsed = !settingsCollapsed"
          >
            <el-icon><component :is="settingsCollapsed ? ArrowDown : ArrowUp" /></el-icon>
            <span>{{ settingsCollapsed ? '展开设置' : '收起设置' }}</span>
          </div>
          
          <!-- 深度设置（仅新闻溯源Agent显示） -->
          <transition name="settings-slide">
            <div v-if="selectedAgent?.id === 'news_trace' && !settingsCollapsed" class="depth-settings welcome-depth">
            <div class="depth-label">
              <el-icon><DataAnalysis /></el-icon>
              <span>溯源深度：</span>
            </div>
            <el-radio-group v-model="traceDepth" size="small" class="depth-selector">
              <el-radio-button :label="1">浅层</el-radio-button>
              <el-radio-button :label="2">中等</el-radio-button>
              <el-radio-button :label="3">深层</el-radio-button>
              <el-radio-button :label="4">极深</el-radio-button>
            </el-radio-group>
            <div class="depth-hint">
              <el-icon><InfoFilled /></el-icon>
              <span>{{ getDepthHint(traceDepth) }}</span>
            </div>
          </div>
          </transition>
          <!-- 金融分析输入表单（仅金融量化Agent显示） -->
          <transition name="settings-slide">
            <div v-if="selectedAgent?.id === 'finance_quant' && !settingsCollapsed" class="financial-settings welcome-financial">
            <!-- 模式切换 -->
            <div class="mode-selector">
              <el-radio-group v-model="financialMode" size="small" @change="onFinancialModeChange">
                <el-radio-button label="analysis">
                  <el-icon><DataAnalysis /></el-icon>
                  <span style="margin-left: 4px;">单股票分析</span>
                </el-radio-button>
                <el-radio-button label="recommendation">
                  <el-icon><Star /></el-icon>
                  <span style="margin-left: 4px;">股票推荐</span>
                </el-radio-button>
                <el-radio-button label="backtest">
                  <el-icon><TrendCharts /></el-icon>
                  <span style="margin-left: 4px;">策略回测</span>
                </el-radio-button>
                <el-radio-button label="prediction">
                  <el-icon><TrendCharts /></el-icon>
                  <span style="margin-left: 4px;">股票预测</span>
                </el-radio-button>
              </el-radio-group>
            </div>
            
            <!-- 单股票分析表单 -->
            <div v-if="financialMode === 'analysis'" class="financial-form">
              <el-form :inline="true" size="small">
                <el-form-item label="股票代码">
                  <el-input 
                    v-model="stockCode" 
                    placeholder="如: 000001"
                    style="width: 120px"
                    :disabled="loading"
                  />
                </el-form-item>
                <el-form-item label="开始日期">
                  <el-date-picker
                    v-model="startDate"
                    type="date"
                    placeholder="选择日期"
                    format="YYYYMMDD"
                    value-format="YYYYMMDD"
                    style="width: 150px"
                    :disabled="loading"
                  />
                </el-form-item>
                <el-form-item label="结束日期">
                  <el-date-picker
                    v-model="endDate"
                    type="date"
                    placeholder="选择日期"
                    format="YYYYMMDD"
                    value-format="YYYYMMDD"
                    style="width: 150px"
                    :disabled="loading"
                  />
                </el-form-item>
              </el-form>
            </div>
            
            <!-- 股票推荐表单 -->
            <div v-else-if="financialMode === 'recommendation'" class="financial-form recommendation-form">
              <el-form :inline="true" size="small">
                <el-form-item label="股票代码">
                  <el-input 
                    v-model="recommendationStockCodes" 
                    placeholder="留空自动获取，或用逗号分隔"
                    style="width: 280px"
                    :disabled="loading"
                  />
                  <div class="form-hint">留空则自动获取热门股票</div>
                </el-form-item>
                <el-form-item label="开始日期">
                  <el-date-picker
                    v-model="startDate"
                    type="date"
                    placeholder="选择日期"
                    format="YYYYMMDD"
                    value-format="YYYYMMDD"
                    style="width: 150px"
                    :disabled="loading"
                  />
                </el-form-item>
                <el-form-item label="结束日期">
                  <el-date-picker
                    v-model="endDate"
                    type="date"
                    placeholder="选择日期"
                    format="YYYYMMDD"
                    value-format="YYYYMMDD"
                    style="width: 150px"
                    :disabled="loading"
                  />
                </el-form-item>
                <el-form-item label="最大推荐数">
                  <el-input-number
                    v-model="maxStocks"
                    :min="1"
                    :max="50"
                    :step="1"
                    style="width: 100px"
                    :disabled="loading"
                  />
                </el-form-item>
                <el-form-item label="最低分数">
                  <el-input-number
                    v-model="minRecommendationScore"
                    :min="0"
                    :max="1"
                    :step="0.1"
                    :precision="1"
                    style="width: 100px"
                    :disabled="loading"
                  />
                </el-form-item>
                <el-form-item label="行业筛选">
                  <el-input 
                    v-model="focusSector" 
                    placeholder="如: 科技、金融"
                    style="width: 120px"
                    :disabled="loading"
                  />
                  <div class="form-hint">可选</div>
                </el-form-item>
              </el-form>
            </div>
            
            <!-- 策略回测表单 -->
            <div v-else-if="financialMode === 'backtest'" class="backtest-form-wrapper">
              <BacktestForm 
                :loading="loading"
                @update:formData="handleBacktestFormUpdate"
                ref="backtestFormRef"
              />
            </div>
            
            <!-- 股票预测表单 -->
            <div v-else-if="financialMode === 'prediction'" class="prediction-form-wrapper">
              <PredictionForm 
                :loading="loading"
                @update:formData="handlePredictionFormUpdate"
                ref="predictionFormRef"
              />
            </div>
            </div>
          </transition>
          <div class="input-container">
            <el-icon class="input-icon"><Plus /></el-icon>
            <el-input
              v-if="selectedAgent?.id !== 'finance_quant'"
              v-model="inputMessage"
              placeholder="询问任何问题"
              @keydown.enter.exact.prevent="sendMessage"
              @keydown.shift.enter.exact="inputMessage += '\n'"
              :disabled="!selectedAgent || loading"
              class="welcome-input"
            />
            <div v-else class="financial-input-hint">
              <el-icon><InfoFilled /></el-icon>
              <span v-if="financialMode === 'analysis'">请填写股票代码和日期范围，然后点击发送开始分析</span>
              <span v-else-if="financialMode === 'recommendation'">请填写日期范围，然后点击发送开始推荐</span>
              <span v-else-if="financialMode === 'backtest'">请填写回测参数，然后点击发送开始回测</span>
              <span v-else-if="financialMode === 'prediction'">请填写预测参数，然后点击发送开始预测</span>
            </div>
            <div class="input-actions">
              <el-button 
                v-if="loading && currentTaskId"
                type="danger" 
                size="small"
                circle
                @click="cancelTask(currentTaskId)"
                class="pause-btn"
                title="暂停任务"
              >
                <el-icon><VideoPause /></el-icon>
              </el-button>
              <el-button 
                v-else
                :type="loading && currentTaskId ? 'danger' : 'primary'"
                @click="handleSendOrCancel"
                :disabled="loading && currentTaskId ? false : (!canSendMessage && !loading)"
                class="send-btn welcome-send-btn"
                circle
              >
                <template v-if="loading && currentTaskId">
                  <el-icon><VideoPause /></el-icon>
                </template>
                <template v-else-if="loading">
                  <el-icon class="is-loading"><Loading /></el-icon>
                </template>
                <template v-else>
                  <el-icon><VideoPlay /></el-icon>
                </template>
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onUnmounted, onMounted, markRaw } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, Plus, VideoPlay, Search, DataAnalysis, Close, VideoPause, InfoFilled, Star, TrendCharts, ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import NewsTraceResult from '@/components/NewsTraceResult.vue'
import FinancialResult from '@/components/FinancialResult.vue'
import StockRecommendationResult from '@/components/StockRecommendationResult.vue'
import BacktestForm from '@/components/BacktestForm.vue'
import BacktestResult from '@/components/BacktestResult.vue'
import PredictionForm from '@/components/PredictionForm.vue'
import PredictionResult from '@/components/PredictionResult.vue'
import { traceNewsAsync, getTaskStatus, cancelTask as cancelTaskAPI, analyzeStockAsync, getFinancialTaskStatus, cancelFinancialTask, recommendStocksAsync, getRecommendationTaskStatus, cancelRecommendationTask, backtestStrategy, predictStockPriceAsync, getPredictionTaskStatus, cancelPredictionTask } from '@/api/agent'
import { saveChatHistory, getChatHistory, generateChatId } from '@/utils/chatHistory'

const selectedAgent = ref(null)
const currentChatId = ref(null) // 当前对话的唯一 ID
const inputMessage = ref('')
const messages = ref([])
const loading = ref(false)
const messagesContainer = ref(null)
const currentTaskId = ref(null) // 当前任务ID
const traceDepth = ref(2) // 默认中等深度
// 金融分析输入
const stockCode = ref('')
const startDate = ref('')
const endDate = ref('')
// 金融模式：'analysis' (单股票分析)、'recommendation' (股票推荐) 或 'backtest' (策略回测)
const financialMode = ref('analysis')
// 回测表单数据
const backtestFormData = ref(null)
const backtestFormRef = ref(null)

// 处理回测表单数据更新
const handleBacktestFormUpdate = (formData) => {
  console.log('[ChatView] BacktestForm update received:', formData)
  console.log('[ChatView] Before update - backtestFormData.value:', backtestFormData.value)
  backtestFormData.value = formData
  console.log('[ChatView] After update - backtestFormData.value:', backtestFormData.value)
  console.log('[ChatView] Stock code:', formData?.stock_code, 'Start date:', formData?.start_date, 'End date:', formData?.end_date)
}

// 股票预测表单数据
const predictionFormData = ref(null)
const predictionFormRef = ref(null)

// 处理股票预测表单数据更新
const handlePredictionFormUpdate = (formData) => {
  console.log('[ChatView] PredictionForm update received:', formData)
  console.log('[ChatView] Before update - predictionFormData.value:', predictionFormData.value)
  predictionFormData.value = formData
  console.log('[ChatView] After update - predictionFormData.value:', predictionFormData.value)
  console.log('[ChatView] Stock code:', formData?.stock_code, 'Start date:', formData?.start_date, 'End date:', formData?.end_date)
}

// 股票推荐输入
const recommendationStockCodes = ref('') // 用逗号分隔的股票代码，如 "000001,000002"
const maxStocks = ref(10)
const minRecommendationScore = ref(0.5)
const focusSector = ref('')
// 设置面板折叠状态
const settingsCollapsed = ref(false)
// 使用 Map 管理多个任务的轮询，key 是 taskId，value 是 intervalId
const taskPollingIntervals = new Map()
// 金融分析任务的轮询
const financialTaskPollingIntervals = new Map()
// 任务到对话的映射，key 是 taskId，value 是 chatId
const taskToChatId = new Map()
// 金融分析任务到对话的映射
const financialTaskToChatId = new Map()
// 股票推荐任务的轮询
const recommendationTaskPollingIntervals = new Map()
// 股票推荐任务到对话的映射
const recommendationTaskToChatId = new Map()
// 策略回测任务的轮询
const backtestTaskPollingIntervals = new Map()
// 策略回测任务到对话的映射
const backtestTaskToChatId = new Map()
// 股票预测任务的轮询
const predictionTaskPollingIntervals = new Map()
// 股票预测任务到对话的映射
const predictionTaskToChatId = new Map()
// 任务到深度的映射，key 是 taskId，value 是 max_depth
const taskToDepth = new Map()

const agents = ref([
  {
    id: 'news_trace',
    name: '新闻溯源 Agent',
    description: '追踪新闻来源，验证信息真实性',
    icon: markRaw(Search),
    iconComponent: markRaw(Search),
    type: 'trace'
  },
  {
    id: 'finance_quant',
    name: '金融量化 Agent',
    description: '金融数据分析和量化策略',
    icon: markRaw(DataAnalysis),
    iconComponent: markRaw(DataAnalysis),
    type: 'finance',
    disabled: false
  }
])

const selectAgent = (agent) => {
  if (agent.disabled) {
    ElMessage.info('该功能即将推出')
    return
  }
  selectedAgent.value = agent
  // 选择 agent 时生成新的对话 ID
  currentChatId.value = generateChatId(agent.id)
  messages.value = []
  // 清空金融分析输入
  stockCode.value = ''
  startDate.value = ''
  endDate.value = ''
  financialMode.value = 'analysis'
  recommendationStockCodes.value = ''
  maxStocks.value = 10
  minRecommendationScore.value = 0.5
  focusSector.value = ''
  backtestFormData.value = null
  // 不自动加载历史记录，让用户选择
}

// 计算是否可以发送消息
const canSendMessage = computed(() => {
  if (selectedAgent.value?.id === 'finance_quant') {
    if (financialMode.value === 'analysis') {
      // 单股票分析：需要股票代码和日期
      return stockCode.value.trim() && startDate.value && endDate.value
    } else if (financialMode.value === 'recommendation') {
      // 股票推荐：只需要日期（股票代码可选）
      return startDate.value && endDate.value
    } else if (financialMode.value === 'backtest') {
      // 策略回测：优先检查 backtestFormData（通过事件更新），如果不可用则从 ref 获取
      // 这样可以同时支持欢迎界面和对话界面
      if (backtestFormData.value) {
        const hasStockCode = backtestFormData.value.stock_code?.trim()
        const hasDates = backtestFormData.value.start_date && backtestFormData.value.end_date
        if (hasStockCode && hasDates) {
          return true
        }
      }
      // 如果 backtestFormData 没有数据或不完整，尝试从 ref 获取
      if (backtestFormRef.value) {
        try {
          const formData = backtestFormRef.value.getFormData()
          const hasStockCode = formData.stock_code?.trim()
          const hasDates = formData.start_date && formData.end_date
          return !!(hasStockCode && hasDates)
        } catch (error) {
          return false
        }
      }
      return false
    } else if (financialMode.value === 'prediction') {
      // 股票预测：优先检查 predictionFormData（通过事件更新），如果不可用则从 ref 获取
      if (predictionFormData.value) {
        const hasStockCode = predictionFormData.value.stock_code?.trim()
        const hasDates = predictionFormData.value.start_date && predictionFormData.value.end_date
        if (hasStockCode && hasDates) {
          return true
        }
      }
      // 如果 predictionFormData 没有数据或不完整，尝试从 ref 获取
      if (predictionFormRef.value) {
        try {
          const formData = predictionFormRef.value.getFormData()
          const hasStockCode = formData.stock_code?.trim()
          const hasDates = formData.start_date && formData.end_date
          return !!(hasStockCode && hasDates)
        } catch (error) {
          return false
        }
      }
      return false
    }
  }
  return inputMessage.value.trim()
})

// 金融模式切换处理
const onFinancialModeChange = () => {
  // 切换模式时清空相关输入
  if (financialMode.value === 'analysis') {
    recommendationStockCodes.value = ''
    maxStocks.value = 10
    minRecommendationScore.value = 0.5
    focusSector.value = ''
    backtestFormData.value = null
    predictionFormData.value = null
  } else if (financialMode.value === 'recommendation') {
    stockCode.value = ''
    backtestFormData.value = null
    predictionFormData.value = null
  } else if (financialMode.value === 'backtest') {
    stockCode.value = ''
    recommendationStockCodes.value = ''
    maxStocks.value = 10
    minRecommendationScore.value = 0.5
    focusSector.value = ''
    predictionFormData.value = null
  } else if (financialMode.value === 'prediction') {
    stockCode.value = ''
    recommendationStockCodes.value = ''
    maxStocks.value = 10
    minRecommendationScore.value = 0.5
    focusSector.value = ''
    backtestFormData.value = null
  }
}

// 格式化进度显示（保留一位小数）
const formatProgress = (percentage) => {
  return `${percentage.toFixed(1)}%`
}

// 获取深度提示信息
const getDepthHint = (depth) => {
  const hints = {
    1: '快速搜索，约1-2轮，适合简单查询',
    2: '标准搜索，约3-5轮，推荐使用',
    3: '深度搜索，约6-8轮，更全面分析',
    4: '极深搜索，约9-10轮，最全面但耗时较长'
  }
  return hints[depth] || hints[2]
}

// 处理发送或取消
const handleSendOrCancel = () => {
  if (loading.value && currentTaskId.value) {
    // 如果正在运行且有任务ID，则取消任务
    cancelTask(currentTaskId.value)
  } else if (!loading.value && canSendMessage.value) {
    // 否则发送消息（使用 canSendMessage 判断，支持新闻溯源和金融量化两种模式）
    sendMessage()
  }
}

const sendMessage = async () => {
  if (!selectedAgent.value || loading.value) {
    return
  }

  // 验证输入
  if (selectedAgent.value.id === 'finance_quant') {
    if (financialMode.value === 'analysis') {
      // 单股票分析模式
      if (!stockCode.value.trim() || !startDate.value || !endDate.value) {
        ElMessage.warning('请填写股票代码和日期范围')
        return
      }
    } else if (financialMode.value === 'recommendation') {
      // 股票推荐模式
      if (!startDate.value || !endDate.value) {
        ElMessage.warning('请填写日期范围')
        return
      }
    } else if (financialMode.value === 'backtest') {
      // 策略回测模式：优先使用 backtestFormData，如果不可用则从 ref 获取
      let formDataToValidate = null
      
      if (backtestFormData.value) {
        // 使用事件更新的数据
        formDataToValidate = backtestFormData.value
      } else if (backtestFormRef.value) {
        // 从 ref 获取数据
        try {
          formDataToValidate = backtestFormRef.value.getFormData()
        } catch (error) {
          console.error('Error getting form data from ref:', error)
        }
      }
      
      if (!formDataToValidate) {
        ElMessage.warning('回测表单未初始化，请稍后再试')
        return
      }
      
      // 手动验证关键字段
      if (!formDataToValidate.stock_code?.trim()) {
        ElMessage.warning('请输入股票代码')
        return
      }
      if (!formDataToValidate.start_date || !formDataToValidate.end_date) {
        ElMessage.warning('请选择回测期间')
        return
      }
      
      // 如果 ref 可用，也调用其 validate 方法进行完整验证
      if (backtestFormRef.value) {
        const validation = backtestFormRef.value.validate()
        if (!validation.valid) {
          ElMessage.warning(validation.message)
          return
        }
      }
    } else if (financialMode.value === 'prediction') {
      // 股票预测模式：日期验证在 prediction 模式的处理逻辑中进行
      // 这里不需要验证，因为预测模式使用 predictionFormData 中的日期
    }
    // 验证日期格式（仅对 analysis 和 recommendation 模式）
    if ((financialMode.value === 'analysis' || financialMode.value === 'recommendation') && (startDate.value.length !== 8 || endDate.value.length !== 8)) {
      ElMessage.warning('日期格式错误，应为 YYYYMMDD')
      return
    }
    // 验证日期顺序（仅对 analysis 和 recommendation 模式）
    if ((financialMode.value === 'analysis' || financialMode.value === 'recommendation') && startDate.value > endDate.value) {
      ElMessage.warning('开始日期不能晚于结束日期')
      return
    }
  } else {
    if (!inputMessage.value.trim()) {
      return
    }
  }

  // 如果没有当前对话 ID，生成一个新的
  if (!currentChatId.value && selectedAgent.value) {
    currentChatId.value = generateChatId(selectedAgent.value.id)
  }

  const userMessage = {
    role: 'user',
    content: selectedAgent.value.id === 'finance_quant' 
      ? (financialMode.value === 'analysis' 
          ? `分析股票 ${stockCode.value} (${startDate.value} 至 ${endDate.value})`
          : financialMode.value === 'recommendation'
            ? `股票推荐 (${startDate.value} 至 ${endDate.value})${recommendationStockCodes.value.trim() ? ` - 指定股票: ${recommendationStockCodes.value}` : ''}`
            : financialMode.value === 'backtest'
              ? `策略回测 ${backtestFormData.value?.stock_code || ''} (${backtestFormData.value?.start_date || ''} 至 ${backtestFormData.value?.end_date || ''})`
              : `股票预测 ${predictionFormData.value?.stock_code || ''} (${predictionFormData.value?.start_date || ''} 至 ${predictionFormData.value?.end_date || ''})`)
      : inputMessage.value.trim(),
    timestamp: new Date().toISOString()
  }

  messages.value.push(userMessage)
  const currentInput = selectedAgent.value.id === 'finance_quant' 
    ? (financialMode.value === 'analysis' 
        ? `分析股票 ${stockCode.value} (${startDate.value} 至 ${endDate.value})`
        : financialMode.value === 'recommendation'
          ? `股票推荐 (${startDate.value} 至 ${endDate.value})`
          : `策略回测 ${backtestFormData.value?.stock_code || ''} (${backtestFormData.value?.start_date || ''} 至 ${backtestFormData.value?.end_date || ''})`)
    : inputMessage.value.trim()
  
  if (selectedAgent.value.id !== 'finance_quant') {
    inputMessage.value = ''
  }
  loading.value = true

  // 立即保存用户消息到历史记录
  if (selectedAgent.value && currentChatId.value) {
    saveChatHistory(currentChatId.value, {
      agent: selectedAgent.value,
      messages: messages.value
    })
    // 通知侧边栏刷新历史记录
    window.dispatchEvent(new CustomEvent('chat-history-updated'))
  }

  // 滚动到底部
  await nextTick()
  scrollToBottom()

  try {
    if (selectedAgent.value.id === 'news_trace') {
      // 使用异步任务 + 轮询机制
      const requestData = { 
        claim: currentInput,
        max_depth: traceDepth.value 
      }
      console.log('创建任务，请求数据:', requestData)
      
      const taskResponse = await traceNewsAsync(requestData)
      const taskId = taskResponse.task_id
      
      if (!taskId) {
        throw new Error('任务创建失败：未返回任务ID')
      }
      
      console.log('任务创建成功，taskId:', taskId, 'status:', taskResponse.status)
      
      currentTaskId.value = taskId // 保存当前任务ID
      
      // 保存任务深度映射
      taskToDepth.set(taskId, traceDepth.value)
      
      // 保存任务到当前对话的映射
      if (currentChatId.value) {
        taskToChatId.set(taskId, currentChatId.value)
      }
      
      // 添加一个进度消息
      const progressMessageObj = {
        role: 'assistant',
        type: 'progress',
        content: taskResponse.message || '任务已创建',
        progress: taskResponse.progress || 0,
        taskId: taskId,
        status: taskResponse.status || 'processing', // 确保状态被保存
        timestamp: new Date().toISOString()
      }
      messages.value.push(progressMessageObj)
      
      // 立即保存包含进度消息的历史记录
      if (selectedAgent.value && currentChatId.value) {
        saveChatHistory(currentChatId.value, {
          agent: selectedAgent.value,
          messages: messages.value
        })
        window.dispatchEvent(new CustomEvent('chat-history-updated'))
      }
      
      await nextTick()
      scrollToBottom()
      
      // 开始轮询任务状态（不等待，让它在后台运行）
      pollTaskStatus(taskId, progressMessageObj).catch(error => {
        console.error('启动轮询失败:', error)
        ElMessage.error('启动任务状态轮询失败')
        loading.value = false
        currentTaskId.value = null
      })
      
      // 注意：不在这里设置 loading = false，让轮询完成后设置
    } else if (selectedAgent.value.id === 'finance_quant') {
      if (financialMode.value === 'analysis') {
        // 单股票分析任务
        const requestData = {
          stock_code: stockCode.value.trim(),
          start_date: startDate.value,
          end_date: endDate.value
        }
        console.log('创建金融分析任务，请求数据:', requestData)
        
        const taskResponse = await analyzeStockAsync(requestData)
        const taskId = taskResponse.task_id
        
        if (!taskId) {
          throw new Error('任务创建失败：未返回任务ID')
        }
        
        console.log('金融分析任务创建成功，taskId:', taskId, 'status:', taskResponse.status)
        
        currentTaskId.value = taskId
        
        // 保存任务到当前对话的映射
        if (currentChatId.value) {
          financialTaskToChatId.set(taskId, currentChatId.value)
        }
        
        // 添加一个进度消息
        const progressMessageObj = {
          role: 'assistant',
          type: 'progress',
          content: taskResponse.message || '任务已创建',
          progress: taskResponse.progress || 0,
          taskId: taskId,
          status: taskResponse.status || 'processing',
          timestamp: new Date().toISOString()
        }
        messages.value.push(progressMessageObj)
        
        // 立即保存包含进度消息的历史记录
        if (selectedAgent.value && currentChatId.value) {
          saveChatHistory(currentChatId.value, {
            agent: selectedAgent.value,
            messages: messages.value
          })
          window.dispatchEvent(new CustomEvent('chat-history-updated'))
        }
        
        await nextTick()
        scrollToBottom()
        
        // 开始轮询金融分析任务状态
        pollFinancialTaskStatus(taskId, progressMessageObj).catch(error => {
          console.error('启动金融分析轮询失败:', error)
          ElMessage.error('启动任务状态轮询失败')
          loading.value = false
          currentTaskId.value = null
        })
      } else if (financialMode.value === 'recommendation') {
        // 股票推荐任务（异步）
        const requestData = {
          start_date: startDate.value,
          end_date: endDate.value,
          max_stocks: maxStocks.value,
          min_recommendation_score: minRecommendationScore.value
        }
        
        // 如果指定了股票代码，解析并添加到请求中
        if (recommendationStockCodes.value.trim()) {
          const codes = recommendationStockCodes.value
            .split(',')
            .map(code => code.trim())
            .filter(code => code.length > 0)
          if (codes.length > 0) {
            requestData.stock_codes = codes
          }
        }
        
        // 如果指定了行业筛选
        if (focusSector.value.trim()) {
          requestData.focus_sector = focusSector.value.trim()
        }
        
        console.log('创建股票推荐任务，请求数据:', requestData)
        
        const taskResponse = await recommendStocksAsync(requestData)
        const taskId = taskResponse.task_id
        
        if (!taskId) {
          throw new Error('任务创建失败：未返回任务ID')
        }
        
        console.log('股票推荐任务创建成功，taskId:', taskId, 'status:', taskResponse.status)
        
        currentTaskId.value = taskId
        
        // 保存任务到当前对话的映射
        if (currentChatId.value) {
          recommendationTaskToChatId.set(taskId, currentChatId.value)
        }
        
        // 添加一个进度消息
        const progressMessageObj = {
          role: 'assistant',
          type: 'progress',
          content: taskResponse.message || '任务已创建',
          progress: taskResponse.progress || 0,
          taskId: taskId,
          status: taskResponse.status || 'processing',
          timestamp: new Date().toISOString()
        }
        messages.value.push(progressMessageObj)
        
        // 立即保存包含进度消息的历史记录
        if (selectedAgent.value && currentChatId.value) {
          saveChatHistory(currentChatId.value, {
            agent: selectedAgent.value,
            messages: messages.value
          })
          window.dispatchEvent(new CustomEvent('chat-history-updated'))
        }
        
        await nextTick()
        scrollToBottom()
        
        // 开始轮询股票推荐任务状态
        pollRecommendationTaskStatus(taskId, progressMessageObj).catch(error => {
          console.error('启动股票推荐轮询失败:', error)
          ElMessage.error('启动任务状态轮询失败')
          loading.value = false
          currentTaskId.value = null
        })
      } else if (financialMode.value === 'backtest') {
        // 策略回测（同步调用）
        let formData = null
        
        // 优先使用 backtestFormData（通过事件更新，更可靠）
        if (backtestFormData.value && backtestFormData.value.stock_code?.trim() && backtestFormData.value.start_date && backtestFormData.value.end_date) {
          formData = { ...backtestFormData.value }
          console.log('[ChatView] 使用 backtestFormData:', formData)
        } else if (backtestFormRef.value) {
          // 如果 backtestFormData 不可用，从 ref 获取
          try {
            // 先验证
            const validation = backtestFormRef.value.validate()
            if (!validation.valid) {
              ElMessage.warning(validation.message)
              loading.value = false
              return
            }
            formData = backtestFormRef.value.getFormData()
            console.log('[ChatView] 使用 ref getFormData:', formData)
          } catch (error) {
            console.error('[ChatView] 获取表单数据失败:', error)
            ElMessage.error('获取表单数据失败')
            loading.value = false
            return
          }
        } else {
          ElMessage.warning('回测表单未初始化')
          loading.value = false
          return
        }
        
        // 最终验证
        if (!formData.stock_code?.trim()) {
          ElMessage.warning('请输入股票代码')
          loading.value = false
          return
        }
        if (!formData.start_date || !formData.end_date) {
          ElMessage.warning('请选择回测期间')
          loading.value = false
          return
        }
        
        console.log('[ChatView] 策略回测请求数据:', formData)
        
        try {
          const result = await backtestStrategy(formData)
          
          console.log('策略回测完成，结果:', result)
          
          // 创建回测结果消息
          const backtestMessage = createBacktestResultMessage(result)
          messages.value.push(backtestMessage)
          
          // 保存到历史记录
          if (selectedAgent.value && currentChatId.value) {
            saveChatHistory(currentChatId.value, {
              agent: selectedAgent.value,
              messages: messages.value
            })
            window.dispatchEvent(new CustomEvent('chat-history-updated'))
          }
          
          loading.value = false
          currentTaskId.value = null
          
          await nextTick()
          scrollToBottom()
          
          ElMessage.success(`回测完成：总收益率 ${result.metrics.total_return_rate >= 0 ? '+' : ''}${result.metrics.total_return_rate.toFixed(2)}%`)
        } catch (error) {
          console.error('Error during backtest:', error)
          ElMessage.error(error.message || '回测失败，请稍后重试')
          loading.value = false
          currentTaskId.value = null
          await nextTick()
          scrollToBottom()
        }
      } else if (financialMode.value === 'prediction') {
        // 股票预测（异步任务）
        let formData = null
        
        // 优先使用 predictionFormData（通过事件更新，更可靠）
        if (predictionFormData.value && predictionFormData.value.stock_code?.trim() && predictionFormData.value.start_date && predictionFormData.value.end_date) {
          formData = { ...predictionFormData.value }
          console.log('[ChatView] 使用 predictionFormData:', formData)
        } else if (predictionFormRef.value) {
          // 如果 predictionFormData 不可用，从 ref 获取
          try {
            // 先验证
            const validation = predictionFormRef.value.validate()
            if (!validation.valid) {
              ElMessage.warning(validation.message)
              loading.value = false
              return
            }
            formData = predictionFormRef.value.getFormData()
            console.log('[ChatView] 使用 ref getFormData:', formData)
          } catch (error) {
            console.error('[ChatView] 获取表单数据失败:', error)
            ElMessage.error('获取表单数据失败')
            loading.value = false
            return
          }
        } else {
          ElMessage.warning('预测表单未初始化')
          loading.value = false
          return
        }
        
        // 最终验证
        if (!formData.stock_code?.trim()) {
          ElMessage.warning('请输入股票代码')
          loading.value = false
          return
        }
        if (!formData.start_date || !formData.end_date) {
          ElMessage.warning('请选择训练期间')
          loading.value = false
          return
        }
        
        console.log('[ChatView] 股票预测请求数据:', formData)
        
        try {
          // 创建异步预测任务
          const taskResponse = await predictStockPriceAsync(formData)
          const taskId = taskResponse.task_id
          
          if (!taskId) {
            throw new Error('任务创建失败：未返回任务ID')
          }
          
          console.log('股票预测任务创建成功，taskId:', taskId, 'status:', taskResponse.status)
          
          currentTaskId.value = taskId
          
          // 保存任务到当前对话的映射
          if (currentChatId.value) {
            predictionTaskToChatId.set(taskId, currentChatId.value)
          }
          
          // 添加一个进度消息
          const progressMessageObj = {
            role: 'assistant',
            type: 'progress',
            content: taskResponse.message || '预测任务已创建',
            progress: taskResponse.progress || 0,
            taskId: taskId,
            status: taskResponse.status || 'processing',
            timestamp: new Date().toISOString()
          }
          messages.value.push(progressMessageObj)
          
          // 立即保存包含进度消息的历史记录
          if (selectedAgent.value && currentChatId.value) {
            saveChatHistory(currentChatId.value, {
              agent: selectedAgent.value,
              messages: messages.value
            })
            window.dispatchEvent(new CustomEvent('chat-history-updated'))
          }
          
          await nextTick()
          scrollToBottom()
          
          // 开始轮询股票预测任务状态
          pollPredictionTaskStatus(taskId, progressMessageObj).catch(error => {
            console.error('启动股票预测轮询失败:', error)
            ElMessage.error('启动任务状态轮询失败')
            loading.value = false
            currentTaskId.value = null
          })
        } catch (error) {
          console.error('Error during prediction:', error)
          ElMessage.error(error.message || '预测失败，请稍后重试')
          loading.value = false
          currentTaskId.value = null
          await nextTick()
          scrollToBottom()
        }
      }
    } else {
      // 其他 agent 的处理
      ElMessage.info('该功能暂未实现')
      loading.value = false
    }

  } catch (error) {
    ElMessage.error(error.message || '请求失败，请稍后重试')
    console.error('Error creating task:', error)
    // 移除进度消息（如果存在）
    const progressIndex = messages.value.findIndex(m => m.type === 'progress')
    if (progressIndex !== -1) {
      messages.value.splice(progressIndex, 1)
    }
    loading.value = false
    currentTaskId.value = null
    await nextTick()
    scrollToBottom()
  }
}

const clearChat = () => {
  messages.value = []
  if (selectedAgent.value) {
    // 清空对话时生成新的 chatId
    currentChatId.value = generateChatId(selectedAgent.value.id)
    saveChatHistory(currentChatId.value, {
      agent: selectedAgent.value,
      messages: []
    })
    // 通知侧边栏刷新历史记录
    window.dispatchEvent(new CustomEvent('chat-history-updated'))
  }
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}


// 监听消息变化，自动滚动
watch(messages, () => {
  nextTick(() => {
    scrollToBottom()
  })
}, { deep: true })

// 从 sidebar 加载历史记录的方法
const loadHistory = (history) => {
  if (history && history.agent) {
    // 注意：不要停止正在进行的轮询，让任务继续在后台运行
    
    selectedAgent.value = history.agent
    // 设置当前对话 ID
    currentChatId.value = history.chatId || history.agentId
    if (history.messages && history.messages.length > 0) {
      messages.value = history.messages
      
      // 检查是否有未完成的任务（progress 类型的消息且状态不是已完成/失败/取消）
      const progressMessage = history.messages.find(
        m => m.type === 'progress' && 
        m.taskId && 
        m.status !== 'completed' && 
        m.status !== 'failed' && 
        m.status !== 'cancelled'
      )
      
      if (progressMessage && progressMessage.taskId) {
        const taskId = progressMessage.taskId
        
        // 判断任务类型
        const isFinancialTask = financialTaskToChatId.has(taskId)
        const isRecommendationTask = recommendationTaskToChatId.has(taskId)
        const isPredictionTask = predictionTaskToChatId.has(taskId)
        
        // 确保任务映射已保存
        if (currentChatId.value) {
          if (isPredictionTask) {
            predictionTaskToChatId.set(taskId, currentChatId.value)
          } else if (isRecommendationTask) {
            recommendationTaskToChatId.set(taskId, currentChatId.value)
          } else if (isFinancialTask) {
            financialTaskToChatId.set(taskId, currentChatId.value)
          } else {
            taskToChatId.set(taskId, currentChatId.value)
          }
        }
        
        // 检查该任务是否已经在轮询中
        const isPolling = taskPollingIntervals.has(taskId) || 
                         financialTaskPollingIntervals.has(taskId) || 
                         recommendationTaskPollingIntervals.has(taskId) ||
                         predictionTaskPollingIntervals.has(taskId)
        
        if (!isPolling) {
          currentTaskId.value = taskId
          loading.value = true
          if (isPredictionTask) {
            pollPredictionTaskStatus(taskId, progressMessage).catch(error => {
              console.error('恢复股票预测轮询失败:', error)
              loading.value = false
              currentTaskId.value = null
            })
          } else if (isRecommendationTask) {
            pollRecommendationTaskStatus(taskId, progressMessage).catch(error => {
              console.error('恢复股票推荐轮询失败:', error)
              loading.value = false
              currentTaskId.value = null
            })
          } else if (isFinancialTask) {
            checkAndResumeFinancialTask(taskId, progressMessage)
          } else {
            checkAndResumeTask(taskId, progressMessage)
          }
        } else {
          currentTaskId.value = taskId
          loading.value = true
          if (isPredictionTask) {
            updatePredictionTaskDisplay(taskId)
          } else if (isRecommendationTask) {
            updateRecommendationTaskDisplay(taskId)
          } else if (isFinancialTask) {
            updateFinancialTaskDisplay(taskId)
          } else {
            updateTaskDisplay(taskId)
          }
        }
      } else {
        loading.value = false
        currentTaskId.value = null
      }
      
      nextTick(() => {
        scrollToBottom()
      })
    } else {
      messages.value = []
      loading.value = false
      currentTaskId.value = null
    }
  }
}

// 更新任务显示（不启动新轮询，只更新当前显示）
const updateTaskDisplay = async (taskId) => {
  try {
    const status = await getTaskStatus(taskId)
    const chatId = taskToChatId.get(taskId) || currentChatId.value
    
    if (chatId === currentChatId.value) {
      const taskHistory = getChatHistory(chatId)
      if (taskHistory && taskHistory.messages) {
        const historyProgressMsg = taskHistory.messages.find(m => m.taskId === taskId)
        if (historyProgressMsg) {
          const index = messages.value.findIndex(m => m.taskId === taskId)
          if (index !== -1) {
            messages.value[index] = { ...historyProgressMsg }
          } else {
            messages.value.push({ ...historyProgressMsg })
          }
          
          if (status.status === 'processing' || status.status === 'pending') {
            loading.value = true
            currentTaskId.value = taskId
          } else {
            loading.value = false
            if (status.status === 'completed') {
              currentTaskId.value = null
            }
          }
          
          await nextTick()
          scrollToBottom()
        }
      }
    }
  } catch (error) {
    console.error('更新任务显示失败:', error)
  }
}

// 创建结果消息的辅助函数
const createResultMessage = (result, maxDepth = null) => {
  // 如果结果中没有深度信息，添加当前深度
  if (maxDepth !== null && !result.max_depth) {
    result.max_depth = maxDepth
  }
  return {
    role: 'assistant',
    type: 'trace',
    content: '新闻溯源分析完成',
    data: result,
    timestamp: new Date().toISOString()
  }
}

// 创建金融分析结果消息的辅助函数
const createFinancialResultMessage = (result) => {
  return {
    role: 'assistant',
    type: 'financial',
    content: '金融分析完成',
    data: result,
    timestamp: new Date().toISOString()
  }
}

// 创建股票推荐结果消息的辅助函数
const createStockRecommendationMessage = (result) => {
  return {
    role: 'assistant',
    type: 'stock_recommendation',
    content: '股票推荐完成',
    data: result,
    timestamp: new Date().toISOString()
  }
}

// 创建策略回测结果消息的辅助函数
const createBacktestResultMessage = (result) => {
  return {
    role: 'assistant',
    type: 'backtest',
    content: '策略回测完成',
    data: result,
    timestamp: new Date().toISOString()
  }
}

const createPredictionResultMessage = (result) => {
  return {
    role: 'assistant',
    type: 'prediction',
    content: '股票预测完成',
    data: result,
    timestamp: new Date().toISOString()
  }
}

// 检查并恢复任务
const checkAndResumeTask = async (taskId, progressMessageObj) => {
  try {
    const status = await getTaskStatus(taskId)
    
    if (status.status === 'processing' || status.status === 'pending') {
      const index = messages.value.findIndex(m => m.taskId === taskId)
      if (index !== -1) {
        messages.value[index].content = status.message || '处理中...'
        messages.value[index].progress = status.progress || 0
        messages.value[index].status = status.status
      } else {
        messages.value.push({
          role: 'assistant',
          type: 'progress',
          content: status.message || '处理中...',
          progress: status.progress || 0,
          taskId: taskId,
          status: status.status,
          timestamp: new Date().toISOString()
        })
      }
      
      pollTaskStatus(taskId, progressMessageObj).catch(error => {
        console.error('恢复轮询失败:', error)
        loading.value = false
        currentTaskId.value = null
      })
    } else if (status.status === 'completed') {
      loading.value = false
      currentTaskId.value = null
      
      const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
      if (progressIndex !== -1) {
        messages.value.splice(progressIndex, 1)
      }
      
      const existingResult = messages.value.find(
        m => m.role === 'assistant' && 
        m.type === 'trace' && 
        m.data?.original_claim === status.result?.original_claim
      )
      
      if (!existingResult && status.result) {
        const savedDepth = taskToDepth.get(taskId) || traceDepth.value
        messages.value.push(createResultMessage(status.result, savedDepth))
        
        if (selectedAgent.value && currentChatId.value) {
          saveChatHistory(currentChatId.value, {
            agent: selectedAgent.value,
            messages: messages.value
          })
          window.dispatchEvent(new CustomEvent('chat-history-updated'))
        }
      }
      
      await nextTick()
      scrollToBottom()
    } else if (status.status === 'failed' || status.status === 'cancelled') {
      loading.value = false
      currentTaskId.value = null
      
      const index = messages.value.findIndex(m => m.taskId === taskId)
      if (index !== -1) {
        messages.value[index].content = status.status === 'cancelled' ? '任务已取消' : (status.error || '任务处理失败')
        messages.value[index].status = status.status
      }
    }
  } catch (error) {
    console.error('检查任务状态失败:', error)
    if (error.response?.status === 404) {
      loading.value = false
      currentTaskId.value = null
      const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
      if (progressIndex !== -1) {
        messages.value.splice(progressIndex, 1)
      }
    }
  }
}

// 取消任务
const cancelTask = async (taskId) => {
  try {
    // 判断是哪种任务类型
    const isFinancialTask = financialTaskToChatId.has(taskId)
    const isRecommendationTask = recommendationTaskToChatId.has(taskId)
    const isPredictionTask = predictionTaskToChatId.has(taskId)
    
    if (isPredictionTask) {
      await cancelPredictionTask(taskId)
    } else if (isRecommendationTask) {
      await cancelRecommendationTask(taskId)
    } else if (isFinancialTask) {
      await cancelFinancialTask(taskId)
    } else {
      await cancelTaskAPI(taskId)
    }
    
    ElMessage.success('任务已取消')
    
    // 停止轮询
    if (taskPollingIntervals.has(taskId)) {
      clearInterval(taskPollingIntervals.get(taskId))
      taskPollingIntervals.delete(taskId)
    }
    if (financialTaskPollingIntervals.has(taskId)) {
      clearInterval(financialTaskPollingIntervals.get(taskId))
      financialTaskPollingIntervals.delete(taskId)
    }
    if (recommendationTaskPollingIntervals.has(taskId)) {
      clearInterval(recommendationTaskPollingIntervals.get(taskId))
      recommendationTaskPollingIntervals.delete(taskId)
    }
    if (predictionTaskPollingIntervals.has(taskId)) {
      clearInterval(predictionTaskPollingIntervals.get(taskId))
      predictionTaskPollingIntervals.delete(taskId)
    }
    
    const taskChatId = isPredictionTask
      ? predictionTaskToChatId.get(taskId)
      : isRecommendationTask
        ? recommendationTaskToChatId.get(taskId)
        : isFinancialTask 
          ? financialTaskToChatId.get(taskId)
          : taskToChatId.get(taskId)
    
    // 更新对应对话的消息
    updateTaskMessagesInHistory(taskChatId, taskId, {
      content: '任务已取消',
      cancelled: true,
      status: 'cancelled'
    })
    
    // 如果当前对话就是该任务所属的对话，更新显示
    if (taskChatId === currentChatId.value) {
      const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
      if (progressIndex !== -1) {
        messages.value[progressIndex].content = '任务已取消'
        messages.value[progressIndex].cancelled = true
        messages.value[progressIndex].status = 'cancelled'
        messages.value[progressIndex].progress = messages.value[progressIndex].progress || 0
      }
      loading.value = false
      currentTaskId.value = null
    }
    
    // 通知侧边栏刷新历史记录
    window.dispatchEvent(new CustomEvent('chat-history-updated'))
  } catch (error) {
    console.error('Cancel task error:', error)
    ElMessage.error(error.message || '取消任务失败')
  }
}

// 轮询任务状态
const pollTaskStatus = async (taskId, progressMessageObj) => {
  // 如果该任务已经在轮询，先停止旧的轮询
  if (taskPollingIntervals.has(taskId)) {
    clearInterval(taskPollingIntervals.get(taskId))
  }
  
  // 保存任务到当前对话的映射
  if (currentChatId.value) {
    taskToChatId.set(taskId, currentChatId.value)
  }
  
  const maxAttempts = 600 // 最多轮询10分钟（每1秒一次）
  let attempts = 0
  let isCompleted = false // 防止重复处理完成状态
  const taskChatId = taskToChatId.get(taskId) || currentChatId.value // 获取任务所属的对话ID
  
  const intervalId = setInterval(async () => {
    try {
      // 如果已经完成，不再处理
      if (isCompleted) {
        return
      }
      
      attempts++
      if (attempts > maxAttempts) {
        clearInterval(intervalId)
        taskPollingIntervals.delete(taskId)
        // 只在当前对话显示该任务时显示错误
        if (taskChatId === currentChatId.value) {
          ElMessage.warning('任务处理超时，请稍后重试')
          loading.value = false
          currentTaskId.value = null
        }
        return
      }
      
      const status = await getTaskStatus(taskId)
      
      // 检查任务状态
      if (status.status === 'cancelled') {
        if (isCompleted) {
          return
        }
        isCompleted = true
        
        clearInterval(intervalId)
        taskPollingIntervals.delete(taskId)
        
        // 更新对应对话的消息
        updateTaskMessagesInHistory(taskChatId, taskId, {
          content: '任务已取消',
          cancelled: true,
          status: 'cancelled'
        })
        
        // 如果当前对话就是该任务所属的对话，更新显示
        if (taskChatId === currentChatId.value) {
          const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            messages.value[progressIndex].content = '任务已取消'
            messages.value[progressIndex].cancelled = true
            messages.value[progressIndex].status = 'cancelled'
          }
          loading.value = false
          currentTaskId.value = null
        }
        
        return
      } else if (status.status === 'completed') {
        if (isCompleted) {
          return // 防止重复处理
        }
        isCompleted = true
        
        clearInterval(intervalId)
        taskPollingIntervals.delete(taskId)
        
        // 更新对应对话的历史记录
        const taskHistory = getChatHistory(taskChatId)
        if (taskHistory && taskHistory.messages) {
          const progressIndex = taskHistory.messages.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            taskHistory.messages.splice(progressIndex, 1)
          }
          
          const existingResult = taskHistory.messages.find(
            m => m.role === 'assistant' && 
            m.type === 'trace' && 
            m.data?.original_claim === status.result?.original_claim
          )
          
          if (!existingResult && status.result) {
            const savedDepth = taskToDepth.get(taskId) || traceDepth.value
            taskHistory.messages.push(createResultMessage(status.result, savedDepth))
          }
          
          saveChatHistory(taskChatId, {
            agent: taskHistory.agent,
            messages: taskHistory.messages
          })
        }
        
        // 如果当前对话就是该任务所属的对话，更新显示
        if (taskChatId === currentChatId.value) {
          const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            messages.value.splice(progressIndex, 1)
          }
          
          const existingResult = messages.value.find(
            m => m.role === 'assistant' && 
            m.type === 'trace' && 
            m.data?.original_claim === status.result?.original_claim
          )
          
          if (!existingResult && status.result) {
            const savedDepth = taskToDepth.get(taskId) || traceDepth.value
            messages.value.push(createResultMessage(status.result, savedDepth))
          }
          
          loading.value = false
          currentTaskId.value = null
          
          await nextTick()
          scrollToBottom()
        }
        
        // 通知侧边栏刷新历史记录
        window.dispatchEvent(new CustomEvent('chat-history-updated'))
        
        return // 立即返回，不再继续执行
        
      } else if (status.status === 'failed') {
        if (isCompleted) {
          return
        }
        isCompleted = true
        
        clearInterval(intervalId)
        taskPollingIntervals.delete(taskId)
        
        // 更新对应对话的消息
        updateTaskMessagesInHistory(taskChatId, taskId, {
          status: 'failed'
        })
        
        // 如果当前对话就是该任务所属的对话，更新显示
        if (taskChatId === currentChatId.value) {
          const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            messages.value.splice(progressIndex, 1)
          }
          ElMessage.error(status.error || '任务处理失败')
          loading.value = false
          currentTaskId.value = null
        }
        
        return
      }
      
      // 更新进度消息（仅在未完成时）
      // 始终更新对应对话的历史记录（即使当前不在该对话中）
      const taskHistory = getChatHistory(taskChatId)
      if (taskHistory && taskHistory.messages) {
        const historyIndex = taskHistory.messages.findIndex(m => m.taskId === taskId)
        if (historyIndex !== -1) {
          // 更新历史记录中的进度消息
          taskHistory.messages[historyIndex].content = status.message || '处理中...'
          taskHistory.messages[historyIndex].progress = status.progress || 0
          taskHistory.messages[historyIndex].status = status.status
          
          // 每次更新都立即保存历史记录，确保数据不丢失
          saveChatHistory(taskChatId, {
            agent: taskHistory.agent,
            messages: taskHistory.messages
          })
          
          // 定期通知侧边栏刷新（每10秒一次，避免过于频繁）
          if (attempts % 10 === 0) {
            window.dispatchEvent(new CustomEvent('chat-history-updated'))
          }
        } else if (taskChatId === currentChatId.value) {
          // 如果历史记录中找不到，尝试从当前 messages.value 中恢复
          const currentIndex = messages.value.findIndex(m => m.taskId === taskId)
          if (currentIndex !== -1) {
            taskHistory.messages.push({ ...messages.value[currentIndex] })
            saveChatHistory(taskChatId, {
              agent: taskHistory.agent,
              messages: taskHistory.messages
            })
          }
        }
      } else if (taskChatId === currentChatId.value && selectedAgent.value) {
        // 如果当前对话就是该任务所属的对话，尝试创建历史记录
        saveChatHistory(taskChatId, {
          agent: selectedAgent.value,
          messages: messages.value
        })
      }
      
      // 如果当前对话就是该任务所属的对话，更新显示
      if (taskChatId === currentChatId.value) {
        const index = messages.value.findIndex(m => m.taskId === taskId)
        if (index !== -1) {
          messages.value[index].content = status.message || '处理中...'
          messages.value[index].progress = status.progress || 0
          messages.value[index].status = status.status
        } else if (taskHistory && taskHistory.messages) {
          // 如果消息不存在，从历史记录恢复
          const historyProgressMsg = taskHistory.messages.find(m => m.taskId === taskId)
          if (historyProgressMsg) {
            messages.value.push({ ...historyProgressMsg })
          }
        }
        
        await nextTick()
        scrollToBottom()
      }
      
    } catch (error) {
      console.error('Error polling task status:', error)
      // 如果是 404，说明任务不存在或已过期，停止轮询
      if (error.response && error.response.status === 404) {
        if (isCompleted) {
          return
        }
        isCompleted = true
        
        clearInterval(intervalId)
        taskPollingIntervals.delete(taskId)
        
        // 更新历史记录中的进度消息状态
        const taskHistory = getChatHistory(taskChatId)
        if (taskHistory && taskHistory.messages) {
          const progressIndex = taskHistory.messages.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            taskHistory.messages[progressIndex].content = '任务已过期或不存在'
            taskHistory.messages[progressIndex].status = 'failed'
            saveChatHistory(taskChatId, {
              agent: taskHistory.agent,
              messages: taskHistory.messages
            })
          }
        }
        
        // 如果当前对话就是该任务所属的对话，更新显示
        if (taskChatId === currentChatId.value) {
          const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            messages.value[progressIndex].content = '任务已过期或不存在'
            messages.value[progressIndex].status = 'failed'
          }
          ElMessage.warning('任务已过期或不存在，已停止轮询')
          loading.value = false
          currentTaskId.value = null
        }
        
        return
      }
      // 其他错误继续轮询，不中断（但限制重试次数）
      if (attempts > 10 && attempts % 10 === 0) {
        console.warn(`轮询任务 ${taskId} 连续出错，但继续尝试...`)
      }
    }
  }, 1000) // 每1秒轮询一次
  
  // 保存轮询 interval
  taskPollingIntervals.set(taskId, intervalId)
}

// 更新任务消息到历史记录中
const updateTaskMessagesInHistory = (chatId, taskId, updates) => {
  if (!chatId) return
  
  try {
    const history = getChatHistory(chatId)
    if (history?.messages) {
      const index = history.messages.findIndex(m => m.taskId === taskId)
      if (index !== -1) {
        Object.assign(history.messages[index], updates)
        saveChatHistory(chatId, {
          agent: history.agent,
          messages: history.messages
        })
      }
    }
  } catch (error) {
    console.error('更新任务消息到历史记录失败:', error)
  }
}

// 监听来自 sidebar 的历史记录加载事件
const handleLoadHistory = (event) => {
  // 使用 chatId 或 agentId 加载历史记录
  const chatId = event.detail.chatId || event.detail.agentId
  const history = getChatHistory(chatId)
  if (history) {
    loadHistory(history)
  }
}

// 监听新对话事件
const handleNewChat = () => {
  selectedAgent.value = null
  currentChatId.value = null // 清空当前对话 ID
  messages.value = []
  inputMessage.value = ''
  loading.value = false
  currentTaskId.value = null
  // 注意：不清除正在进行的任务轮询，让它们继续在后台运行
}

onMounted(() => {
  window.addEventListener('load-chat-history', handleLoadHistory)
  window.addEventListener('new-chat', handleNewChat)
})

// 轮询金融分析任务状态
const pollFinancialTaskStatus = async (taskId, progressMessageObj) => {
  if (financialTaskPollingIntervals.has(taskId)) {
    clearInterval(financialTaskPollingIntervals.get(taskId))
  }
  
  if (currentChatId.value) {
    financialTaskToChatId.set(taskId, currentChatId.value)
  }
  
  const maxAttempts = 600
  let attempts = 0
  let isCompleted = false
  const taskChatId = financialTaskToChatId.get(taskId) || currentChatId.value
  
  const intervalId = setInterval(async () => {
    try {
      if (isCompleted) return
      
      attempts++
      if (attempts > maxAttempts) {
        clearInterval(intervalId)
        financialTaskPollingIntervals.delete(taskId)
        if (taskChatId === currentChatId.value) {
          ElMessage.warning('任务处理超时，请稍后重试')
          loading.value = false
          currentTaskId.value = null
        }
        return
      }
      
      const status = await getFinancialTaskStatus(taskId)
      
      if (status.status === 'cancelled') {
        if (isCompleted) return
        isCompleted = true
        clearInterval(intervalId)
        financialTaskPollingIntervals.delete(taskId)
        updateTaskMessagesInHistory(taskChatId, taskId, {
          content: '任务已取消',
          cancelled: true,
          status: 'cancelled'
        })
        if (taskChatId === currentChatId.value) {
          const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            messages.value[progressIndex].content = '任务已取消'
            messages.value[progressIndex].cancelled = true
            messages.value[progressIndex].status = 'cancelled'
          }
          loading.value = false
          currentTaskId.value = null
        }
        return
      } else if (status.status === 'completed') {
        if (isCompleted) return
        isCompleted = true
        clearInterval(intervalId)
        financialTaskPollingIntervals.delete(taskId)
        
        const taskHistory = getChatHistory(taskChatId)
        if (taskHistory && taskHistory.messages) {
          const progressIndex = taskHistory.messages.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            taskHistory.messages.splice(progressIndex, 1)
          }
          const existingResult = taskHistory.messages.find(
            m => m.role === 'assistant' && m.type === 'financial' && m.data?.stock_code === status.result?.stock_code
          )
          if (!existingResult && status.result) {
            taskHistory.messages.push(createFinancialResultMessage(status.result))
          }
          saveChatHistory(taskChatId, {
            agent: taskHistory.agent,
            messages: taskHistory.messages
          })
        }
        
        if (taskChatId === currentChatId.value) {
          const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            messages.value.splice(progressIndex, 1)
          }
          const existingResult = messages.value.find(
            m => m.role === 'assistant' && m.type === 'financial' && m.data?.stock_code === status.result?.stock_code
          )
          if (!existingResult && status.result) {
            messages.value.push(createFinancialResultMessage(status.result))
          }
          loading.value = false
          currentTaskId.value = null
          await nextTick()
          scrollToBottom()
        }
        window.dispatchEvent(new CustomEvent('chat-history-updated'))
        return
      } else if (status.status === 'failed') {
        if (isCompleted) return
        isCompleted = true
        clearInterval(intervalId)
        financialTaskPollingIntervals.delete(taskId)
        updateTaskMessagesInHistory(taskChatId, taskId, { status: 'failed' })
        if (taskChatId === currentChatId.value) {
          const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            messages.value.splice(progressIndex, 1)
          }
          ElMessage.error(status.error || '任务处理失败')
          loading.value = false
          currentTaskId.value = null
        }
        return
      }
      
      const taskHistory = getChatHistory(taskChatId)
      if (taskHistory && taskHistory.messages) {
        const historyIndex = taskHistory.messages.findIndex(m => m.taskId === taskId)
        if (historyIndex !== -1) {
          taskHistory.messages[historyIndex].content = status.message || '处理中...'
          taskHistory.messages[historyIndex].progress = status.progress || 0
          taskHistory.messages[historyIndex].status = status.status
          saveChatHistory(taskChatId, {
            agent: taskHistory.agent,
            messages: taskHistory.messages
          })
          if (attempts % 10 === 0) {
            window.dispatchEvent(new CustomEvent('chat-history-updated'))
          }
        }
      }
      
      if (taskChatId === currentChatId.value) {
        const index = messages.value.findIndex(m => m.taskId === taskId)
        if (index !== -1) {
          messages.value[index].content = status.message || '处理中...'
          messages.value[index].progress = status.progress || 0
          messages.value[index].status = status.status
        }
        await nextTick()
        scrollToBottom()
      }
    } catch (error) {
      console.error('轮询金融分析任务状态失败:', error)
      if (error.response?.status === 404) {
        clearInterval(intervalId)
        financialTaskPollingIntervals.delete(taskId)
        if (taskChatId === currentChatId.value) {
          ElMessage.warning('任务已过期或不存在')
          loading.value = false
          currentTaskId.value = null
        }
      }
    }
  }, 1000)
  
  financialTaskPollingIntervals.set(taskId, intervalId)
  console.log(`[金融分析轮询] 开始轮询任务: ${taskId} intervalId: ${intervalId} chatId: ${taskChatId}`)
}

// 轮询股票推荐任务状态
const pollRecommendationTaskStatus = async (taskId, progressMessageObj) => {
  if (recommendationTaskPollingIntervals.has(taskId)) {
    clearInterval(recommendationTaskPollingIntervals.get(taskId))
  }
  
  if (currentChatId.value) {
    recommendationTaskToChatId.set(taskId, currentChatId.value)
  }
  
  const maxAttempts = 600
  let attempts = 0
  let isCompleted = false
  const taskChatId = recommendationTaskToChatId.get(taskId) || currentChatId.value
  
  const intervalId = setInterval(async () => {
    try {
      if (isCompleted) return
      
      attempts++
      if (attempts > maxAttempts) {
        clearInterval(intervalId)
        recommendationTaskPollingIntervals.delete(taskId)
        if (taskChatId === currentChatId.value) {
          ElMessage.warning('任务处理超时，请稍后重试')
          loading.value = false
          currentTaskId.value = null
        }
        return
      }
      
      const status = await getRecommendationTaskStatus(taskId)
      
      if (status.status === 'cancelled') {
        if (isCompleted) return
        isCompleted = true
        clearInterval(intervalId)
        recommendationTaskPollingIntervals.delete(taskId)
        updateTaskMessagesInHistory(taskChatId, taskId, {
          content: '任务已取消',
          cancelled: true,
          status: 'cancelled'
        })
        if (taskChatId === currentChatId.value) {
          const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            messages.value[progressIndex].content = '任务已取消'
            messages.value[progressIndex].cancelled = true
            messages.value[progressIndex].status = 'cancelled'
          }
          loading.value = false
          currentTaskId.value = null
        }
        return
      } else if (status.status === 'completed') {
        if (isCompleted) return
        isCompleted = true
        clearInterval(intervalId)
        recommendationTaskPollingIntervals.delete(taskId)
        
        const taskHistory = getChatHistory(taskChatId)
        if (taskHistory && taskHistory.messages) {
          const progressIndex = taskHistory.messages.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            taskHistory.messages.splice(progressIndex, 1)
          }
          const existingResult = taskHistory.messages.find(
            m => m.role === 'assistant' && m.type === 'stock_recommendation'
          )
          if (!existingResult && status.result) {
            taskHistory.messages.push(createStockRecommendationMessage(status.result))
          }
          saveChatHistory(taskChatId, {
            agent: taskHistory.agent,
            messages: taskHistory.messages
          })
        }
        
        if (taskChatId === currentChatId.value) {
          const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            messages.value.splice(progressIndex, 1)
          }
          const existingResult = messages.value.find(
            m => m.role === 'assistant' && m.type === 'stock_recommendation'
          )
          if (!existingResult && status.result) {
            messages.value.push(createStockRecommendationMessage(status.result))
          }
          loading.value = false
          currentTaskId.value = null
          await nextTick()
          scrollToBottom()
        }
        window.dispatchEvent(new CustomEvent('chat-history-updated'))
        return
      } else if (status.status === 'failed') {
        if (isCompleted) return
        isCompleted = true
        clearInterval(intervalId)
        recommendationTaskPollingIntervals.delete(taskId)
        updateTaskMessagesInHistory(taskChatId, taskId, { status: 'failed' })
        if (taskChatId === currentChatId.value) {
          const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            messages.value.splice(progressIndex, 1)
          }
          ElMessage.error(status.error || '任务处理失败')
          loading.value = false
          currentTaskId.value = null
        }
        return
      }
      
      const taskHistory = getChatHistory(taskChatId)
      if (taskHistory && taskHistory.messages) {
        const historyIndex = taskHistory.messages.findIndex(m => m.taskId === taskId)
        if (historyIndex !== -1) {
          taskHistory.messages[historyIndex].content = status.message || '处理中...'
          taskHistory.messages[historyIndex].progress = status.progress || 0
          taskHistory.messages[historyIndex].status = status.status
          saveChatHistory(taskChatId, {
            agent: taskHistory.agent,
            messages: taskHistory.messages
          })
          if (attempts % 10 === 0) {
            window.dispatchEvent(new CustomEvent('chat-history-updated'))
          }
        }
      }
      
      if (taskChatId === currentChatId.value) {
        const index = messages.value.findIndex(m => m.taskId === taskId)
        if (index !== -1) {
          messages.value[index].content = status.message || '处理中...'
          messages.value[index].progress = status.progress || 0
          messages.value[index].status = status.status
        }
        await nextTick()
        scrollToBottom()
      }
    } catch (error) {
      console.error('轮询股票推荐任务状态失败:', error)
      if (error.response?.status === 404) {
        clearInterval(intervalId)
        recommendationTaskPollingIntervals.delete(taskId)
        if (taskChatId === currentChatId.value) {
          ElMessage.warning('任务已过期或不存在')
          loading.value = false
          currentTaskId.value = null
        }
      }
    }
  }, 1000)
  
  recommendationTaskPollingIntervals.set(taskId, intervalId)
  console.log(`[股票推荐轮询] 开始轮询任务: ${taskId} intervalId: ${intervalId} chatId: ${taskChatId}`)
}

// 更新股票推荐任务显示（不启动新轮询，只更新当前显示）
const updateRecommendationTaskDisplay = async (taskId) => {
  try {
    const status = await getRecommendationTaskStatus(taskId)
    const chatId = recommendationTaskToChatId.get(taskId) || currentChatId.value
    
    if (chatId === currentChatId.value) {
      const taskHistory = getChatHistory(chatId)
      if (taskHistory && taskHistory.messages) {
        const historyProgressMsg = taskHistory.messages.find(m => m.taskId === taskId)
        if (historyProgressMsg) {
          const index = messages.value.findIndex(m => m.taskId === taskId)
          if (index !== -1) {
            messages.value[index] = { ...historyProgressMsg }
          } else {
            messages.value.push({ ...historyProgressMsg })
          }
          
          if (status.status === 'processing' || status.status === 'pending') {
            loading.value = true
            currentTaskId.value = taskId
          } else {
            loading.value = false
            if (status.status === 'completed') {
              currentTaskId.value = null
            }
          }
          
          await nextTick()
          scrollToBottom()
        }
      }
    }
  } catch (error) {
    console.error('更新股票推荐任务显示失败:', error)
  }
}

// 更新金融分析任务显示（不启动新轮询，只更新当前显示）
const updateFinancialTaskDisplay = async (taskId) => {
  try {
    const status = await getFinancialTaskStatus(taskId)
    const chatId = financialTaskToChatId.get(taskId) || currentChatId.value
    
    if (chatId === currentChatId.value) {
      const taskHistory = getChatHistory(chatId)
      if (taskHistory && taskHistory.messages) {
        const historyProgressMsg = taskHistory.messages.find(m => m.taskId === taskId)
        if (historyProgressMsg) {
          const index = messages.value.findIndex(m => m.taskId === taskId)
          if (index !== -1) {
            messages.value[index] = { ...historyProgressMsg }
          } else {
            messages.value.push({ ...historyProgressMsg })
          }
          
          if (status.status === 'processing' || status.status === 'pending') {
            loading.value = true
            currentTaskId.value = taskId
          } else {
            loading.value = false
            if (status.status === 'completed') {
              currentTaskId.value = null
            }
          }
          
          await nextTick()
          scrollToBottom()
        }
      }
    }
  } catch (error) {
    console.error('更新金融分析任务显示失败:', error)
  }
}

// 检查并恢复金融分析任务
const checkAndResumeFinancialTask = async (taskId, progressMessageObj) => {
  try {
    const status = await getFinancialTaskStatus(taskId)
    
    if (status.status === 'processing' || status.status === 'pending') {
      const index = messages.value.findIndex(m => m.taskId === taskId)
      if (index !== -1) {
        messages.value[index].content = status.message || '处理中...'
        messages.value[index].progress = status.progress || 0
        messages.value[index].status = status.status
      } else {
        messages.value.push({
          role: 'assistant',
          type: 'progress',
          content: status.message || '处理中...',
          progress: status.progress || 0,
          taskId: taskId,
          status: status.status,
          timestamp: new Date().toISOString()
        })
      }
      
      pollFinancialTaskStatus(taskId, progressMessageObj).catch(error => {
        console.error('恢复金融分析轮询失败:', error)
        loading.value = false
        currentTaskId.value = null
      })
    } else if (status.status === 'completed') {
      loading.value = false
      currentTaskId.value = null
      
      const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
      if (progressIndex !== -1) {
        messages.value.splice(progressIndex, 1)
      }
      
      const existingResult = messages.value.find(
        m => m.role === 'assistant' && 
        m.type === 'financial' && 
        m.data?.stock_code === status.result?.stock_code
      )
      
      if (!existingResult && status.result) {
        messages.value.push(createFinancialResultMessage(status.result))
        
        if (selectedAgent.value && currentChatId.value) {
          saveChatHistory(currentChatId.value, {
            agent: selectedAgent.value,
            messages: messages.value
          })
          window.dispatchEvent(new CustomEvent('chat-history-updated'))
        }
      }
      
      await nextTick()
      scrollToBottom()
    } else if (status.status === 'failed' || status.status === 'cancelled') {
      loading.value = false
      currentTaskId.value = null
      
      const index = messages.value.findIndex(m => m.taskId === taskId)
      if (index !== -1) {
        messages.value[index].content = status.status === 'cancelled' ? '任务已取消' : (status.error || '任务处理失败')
        messages.value[index].status = status.status
      }
    }
  } catch (error) {
    console.error('检查金融分析任务状态失败:', error)
    if (error.response?.status === 404) {
      loading.value = false
      currentTaskId.value = null
      const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
      if (progressIndex !== -1) {
        messages.value.splice(progressIndex, 1)
      }
    }
  }
}

// 轮询股票预测任务状态
const pollPredictionTaskStatus = async (taskId, progressMessageObj) => {
  if (predictionTaskPollingIntervals.has(taskId)) {
    clearInterval(predictionTaskPollingIntervals.get(taskId))
  }
  
  if (currentChatId.value) {
    predictionTaskToChatId.set(taskId, currentChatId.value)
  }
  
  const maxAttempts = 600
  let attempts = 0
  let isCompleted = false
  const taskChatId = predictionTaskToChatId.get(taskId) || currentChatId.value
  
  const intervalId = setInterval(async () => {
    try {
      if (isCompleted) return
      
      attempts++
      if (attempts > maxAttempts) {
        clearInterval(intervalId)
        predictionTaskPollingIntervals.delete(taskId)
        if (taskChatId === currentChatId.value) {
          ElMessage.warning('任务处理超时，请稍后重试')
          loading.value = false
          currentTaskId.value = null
        }
        return
      }
      
      const status = await getPredictionTaskStatus(taskId)
      
      if (status.status === 'cancelled') {
        if (isCompleted) return
        isCompleted = true
        clearInterval(intervalId)
        predictionTaskPollingIntervals.delete(taskId)
        updateTaskMessagesInHistory(taskChatId, taskId, {
          content: '任务已取消',
          cancelled: true,
          status: 'cancelled'
        })
        if (taskChatId === currentChatId.value) {
          const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            messages.value[progressIndex].content = '任务已取消'
            messages.value[progressIndex].cancelled = true
            messages.value[progressIndex].status = 'cancelled'
          }
          loading.value = false
          currentTaskId.value = null
        }
        return
      } else if (status.status === 'completed') {
        if (isCompleted) return
        isCompleted = true
        clearInterval(intervalId)
        predictionTaskPollingIntervals.delete(taskId)
        
        const taskHistory = getChatHistory(taskChatId)
        if (taskHistory && taskHistory.messages) {
          const progressIndex = taskHistory.messages.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            taskHistory.messages.splice(progressIndex, 1)
          }
          const existingResult = taskHistory.messages.find(
            m => m.role === 'assistant' && m.type === 'prediction'
          )
          if (!existingResult && status.result) {
            taskHistory.messages.push(createPredictionResultMessage(status.result))
          }
          saveChatHistory(taskChatId, {
            agent: taskHistory.agent,
            messages: taskHistory.messages
          })
        }
        
        if (taskChatId === currentChatId.value) {
          const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            messages.value.splice(progressIndex, 1)
          }
          const existingResult = messages.value.find(
            m => m.role === 'assistant' && m.type === 'prediction'
          )
          if (!existingResult && status.result) {
            messages.value.push(createPredictionResultMessage(status.result))
          }
          loading.value = false
          currentTaskId.value = null
          await nextTick()
          scrollToBottom()
        }
        window.dispatchEvent(new CustomEvent('chat-history-updated'))
        return
      } else if (status.status === 'failed') {
        if (isCompleted) return
        isCompleted = true
        clearInterval(intervalId)
        predictionTaskPollingIntervals.delete(taskId)
        updateTaskMessagesInHistory(taskChatId, taskId, { status: 'failed' })
        if (taskChatId === currentChatId.value) {
          const progressIndex = messages.value.findIndex(m => m.taskId === taskId)
          if (progressIndex !== -1) {
            messages.value.splice(progressIndex, 1)
          }
          ElMessage.error(status.error || '任务处理失败')
          loading.value = false
          currentTaskId.value = null
        }
        return
      }
      
      const taskHistory = getChatHistory(taskChatId)
      if (taskHistory && taskHistory.messages) {
        const historyIndex = taskHistory.messages.findIndex(m => m.taskId === taskId)
        if (historyIndex !== -1) {
          taskHistory.messages[historyIndex].content = status.message || '处理中...'
          taskHistory.messages[historyIndex].progress = status.progress || 0
          taskHistory.messages[historyIndex].status = status.status
          saveChatHistory(taskChatId, {
            agent: taskHistory.agent,
            messages: taskHistory.messages
          })
          if (attempts % 10 === 0) {
            window.dispatchEvent(new CustomEvent('chat-history-updated'))
          }
        }
      }
      
      if (taskChatId === currentChatId.value) {
        const index = messages.value.findIndex(m => m.taskId === taskId)
        if (index !== -1) {
          messages.value[index].content = status.message || '处理中...'
          messages.value[index].progress = status.progress || 0
          messages.value[index].status = status.status
        }
        await nextTick()
        scrollToBottom()
      }
    } catch (error) {
      console.error('轮询股票预测任务状态失败:', error)
      if (error.response?.status === 404) {
        clearInterval(intervalId)
        predictionTaskPollingIntervals.delete(taskId)
        if (taskChatId === currentChatId.value) {
          ElMessage.warning('任务已过期或不存在')
          loading.value = false
          currentTaskId.value = null
        }
      }
    }
  }, 1000)
  
  predictionTaskPollingIntervals.set(taskId, intervalId)
  console.log(`[股票预测轮询] 开始轮询任务: ${taskId} intervalId: ${intervalId} chatId: ${taskChatId}`)
}

// 更新股票预测任务显示（不启动新轮询，只更新当前显示）
const updatePredictionTaskDisplay = async (taskId) => {
  try {
    const status = await getPredictionTaskStatus(taskId)
    const chatId = predictionTaskToChatId.get(taskId) || currentChatId.value
    
    if (chatId === currentChatId.value) {
      const taskHistory = getChatHistory(chatId)
      if (taskHistory && taskHistory.messages) {
        const historyProgressMsg = taskHistory.messages.find(m => m.taskId === taskId)
        if (historyProgressMsg) {
          const index = messages.value.findIndex(m => m.taskId === taskId)
          if (index !== -1) {
            messages.value[index] = { ...historyProgressMsg }
          } else {
            messages.value.push({ ...historyProgressMsg })
          }
          
          if (status.status === 'processing' || status.status === 'pending') {
            loading.value = true
            currentTaskId.value = taskId
          } else {
            loading.value = false
            if (status.status === 'completed') {
              currentTaskId.value = null
            }
          }
          
          await nextTick()
          scrollToBottom()
        }
      }
    }
  } catch (error) {
    console.error('更新股票预测任务显示失败:', error)
    loading.value = false
    currentTaskId.value = null
  }
}

onUnmounted(() => {
  window.removeEventListener('load-chat-history', handleLoadHistory)
  window.removeEventListener('new-chat', handleNewChat)
  // 清理所有轮询
  taskPollingIntervals.forEach(intervalId => clearInterval(intervalId))
  taskPollingIntervals.clear()
  financialTaskPollingIntervals.forEach(intervalId => clearInterval(intervalId))
  financialTaskPollingIntervals.clear()
  recommendationTaskPollingIntervals.forEach(intervalId => clearInterval(intervalId))
  recommendationTaskPollingIntervals.clear()
  backtestTaskPollingIntervals.forEach(intervalId => clearInterval(intervalId))
  backtestTaskPollingIntervals.clear()
  predictionTaskPollingIntervals.forEach(intervalId => clearInterval(intervalId))
  predictionTaskPollingIntervals.clear()
})


// 暴露方法供父组件调用
defineExpose({
  loadHistory
})
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #ffffff;
  position: relative;
  overflow: hidden;
}

/* 欢迎界面样式 */
.welcome-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  justify-content: space-between;
  padding: 0;
}

.welcome-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.welcome-title {
  font-size: 36px;
  font-weight: 400;
  color: #2d3748;
  margin-bottom: 60px;
  text-align: center;
}

.agent-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  max-width: 800px;
  width: 100%;
}

.agent-card {
  padding: 24px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
  background: #ffffff;
}

.agent-card:hover {
  border-color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
  transform: translateY(-2px);
}

.agent-card.selected {
  border-color: #667eea;
  background: #f7f5ff;
}

.agent-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.agent-card.disabled:hover {
  transform: none;
  box-shadow: none;
}

.agent-icon {
  font-size: 40px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #667eea;
}

.agent-icon .el-icon {
  font-size: 40px;
  width: 40px;
  height: 40px;
}

.agent-name {
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 8px;
}

.agent-desc {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.5;
}

.welcome-input-area {
  padding: 20px;
  border-top: 1px solid #e5e7eb;
  background: #ffffff;
}

.input-container {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 24px;
  background: #ffffff;
  transition: all 0.2s;
  min-height: 56px;
}

.input-container:focus-within {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.input-icon {
  font-size: 20px;
  color: #9ca3af;
  flex-shrink: 0;
}

.welcome-input {
  flex: 1;
}

.welcome-input :deep(.el-input__wrapper) {
  box-shadow: none;
  background: transparent;
}

.welcome-input :deep(.el-input__inner) {
  border: none;
  font-size: 15px;
  color: #2d3748;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.welcome-send-btn {
  width: 40px;
  height: 40px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.welcome-send-btn .el-icon {
  font-size: 18px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 40px 20px;
  background: #ffffff;
  min-height: 0;
  max-width: 1000px;
  margin: 0 auto;
  width: 100%;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.message {
  margin-bottom: 20px;
}

.message-content {
  display: flex;
  flex-direction: column;
}

.message.user .message-content {
  align-items: flex-end;
}

.message.assistant .message-content {
  align-items: flex-start;
}

.message-bubble {
  max-width: 85%;
  padding: 14px 18px;
  border-radius: 12px;
  word-wrap: break-word;
  line-height: 1.6;
}

.user-bubble {
  background: #667eea;
  color: white;
  border-bottom-right-radius: 4px;
}

.assistant-bubble {
  background: #f7f7f8;
  color: #2d3748;
  border-bottom-left-radius: 4px;
}

.progress-message {
  min-width: 300px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.progress-text {
  font-size: 14px;
  flex: 1;
}

.cancel-btn {
  margin-left: 8px;
  flex-shrink: 0;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #999;
  padding: 10px;
}

.progress-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.chat-input-area {
  padding: 20px;
  border-top: 1px solid #e5e7eb;
  background: #ffffff;
}

.depth-settings {
  max-width: 1000px;
  margin: 0 auto 16px;
  padding: 12px 16px;
  background: #f7f5ff;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.welcome-depth {
  max-width: 800px;
  margin: 0 auto 16px;
}

.depth-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #667eea;
  flex-shrink: 0;
}

.depth-selector {
  flex: 1;
  min-width: 300px;
}

.depth-selector :deep(.el-radio-button__inner) {
  padding: 8px 16px;
  font-size: 13px;
}

.depth-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #6b7280;
  flex-shrink: 0;
}

.financial-settings {
  max-width: 800px;
  margin: 0 auto;
  padding: 16px 20px;
  background: #f0f9ff;
  border-radius: 12px;
  border: 1px solid #e0f2fe;
}

.financial-settings.welcome-financial {
  margin-bottom: 12px;
}

.financial-form {
  width: 100%;
}

.financial-form :deep(.el-form) {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  width: 100%;
  justify-content: flex-start;
}

.financial-form :deep(.el-form-item) {
  margin-bottom: 0;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.financial-form :deep(.el-form-item__label) {
  font-size: 14px;
  color: #2d3748;
  font-weight: 500;
  margin-right: 8px;
  white-space: nowrap;
}

.financial-form :deep(.el-input),
.financial-form :deep(.el-date-editor) {
  width: auto;
}

.mode-selector {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
}

.mode-selector :deep(.el-radio-group) {
  width: 100%;
  display: flex;
  gap: 8px;
}

.mode-selector :deep(.el-radio-button) {
  flex: 1;
}

.mode-selector :deep(.el-radio-button__inner) {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
}

.recommendation-form {
  margin-top: 12px;
}

.recommendation-form .form-hint {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
  line-height: 1.4;
}

.financial-input-hint {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0;
  background: transparent;
  font-size: 13px;
  color: #666;
  min-height: auto;
}

.depth-hint .el-icon {
  font-size: 14px;
}

.input-wrapper {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

.chat-input {
  flex: 1;
}

.chat-input :deep(.el-textarea__inner) {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 15px;
  line-height: 1.5;
  resize: none;
  transition: all 0.2s;
}

.chat-input :deep(.el-textarea__inner):focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.send-btn {
  height: 40px;
  padding: 0 24px;
  border-radius: 12px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-btn .el-icon {
  font-size: 16px;
}

.send-btn .is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.pause-btn {
  flex-shrink: 0;
}
</style>

