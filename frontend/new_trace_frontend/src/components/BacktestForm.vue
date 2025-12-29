<template>
  <div class="backtest-form-container">
    <el-form :model="formData" label-width="100px" size="small" :inline="true">
      <el-form-item label="股票代码" required>
        <el-input 
          v-model="formData.stock_code" 
          placeholder="如: 000001"
          style="width: 120px"
          :disabled="loading"
        />
      </el-form-item>
      
      <el-form-item label="回测期间" required>
        <el-date-picker
          v-model="startDate"
          type="date"
          placeholder="开始日期"
          format="YYYYMMDD"
          value-format="YYYYMMDD"
          style="width: 130px"
          :disabled="loading"
        />
        <span style="margin: 0 6px; color: #666;">至</span>
        <el-date-picker
          v-model="endDate"
          type="date"
          placeholder="结束日期"
          format="YYYYMMDD"
          value-format="YYYYMMDD"
          style="width: 130px"
          :disabled="loading"
        />
      </el-form-item>
      
      <el-form-item label="初始资金">
        <el-input-number
          v-model="formData.initial_capital"
          :min="1000"
          :max="10000000"
          :step="10000"
          :precision="0"
          style="width: 150px"
          :disabled="loading"
        />
        <span style="margin-left: 6px; color: #666; font-size: 12px;">元</span>
      </el-form-item>
      
      <el-form-item label="策略类型">
        <el-select 
          v-model="formData.strategy_type" 
          style="width: 150px"
          :disabled="loading"
        >
          <el-option label="信号策略" value="signal_based" />
          <el-option label="均线交叉" value="ma_cross" />
          <el-option label="RSI策略" value="rsi" />
          <el-option label="MACD策略" value="macd" />
        </el-select>
      </el-form-item>
      
      <el-form-item label="每次交易">
        <el-input-number
          v-model="formData.shares_per_trade"
          :min="100"
          :max="10000"
          :step="100"
          :precision="0"
          style="width: 120px"
          :disabled="loading"
        />
        <span style="margin-left: 6px; color: #666; font-size: 12px;">股</span>
      </el-form-item>
      
      <el-form-item label="持有天数">
        <el-input-number
          v-model="formData.hold_days"
          :min="1"
          :max="365"
          :step="1"
          :precision="0"
          style="width: 100px"
          :disabled="loading"
          :clearable="true"
        />
        <span style="margin-left: 6px; color: #999; font-size: 11px;">留空用信号退出</span>
      </el-form-item>
      
      <el-form-item label="信号强度">
        <div class="signal-strength-wrapper">
          <el-slider
            v-model="signalStrength"
            :min="0"
            :max="1"
            :step="0.1"
            :show-tooltip="true"
            :format-tooltip="formatSignalStrength"
            style="width: 200px; margin-right: 10px"
            :disabled="loading"
          />
          <span style="color: #666; font-size: 12px; min-width: 40px;">{{ (signalStrength * 100).toFixed(0) }}%</span>
        </div>
      </el-form-item>
      
      <el-form-item label="信号类型">
        <el-checkbox-group v-model="formData.signal_types" :disabled="loading" size="small">
          <el-checkbox label="buy">买入</el-checkbox>
          <el-checkbox label="sell">卖出</el-checkbox>
          <el-checkbox label="hold">持有</el-checkbox>
        </el-checkbox-group>
        <div style="margin-top: 2px; color: #999; font-size: 11px;">留空使用所有类型</div>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:formData'])

const startDate = ref('')
const endDate = ref('')
const signalStrength = ref(0.5)

const formData = ref({
  stock_code: '',
  start_date: '',
  end_date: '',
  initial_capital: 100000,
  strategy_type: 'signal_based',
  shares_per_trade: 100,
  hold_days: null,
  min_signal_strength: 0.5,
  signal_types: []
})

// 组件挂载时立即触发一次更新事件，确保父组件能获取到初始数据
onMounted(() => {
  console.log('[BacktestForm] Component mounted, initial formData:', formData.value)
  // 使用 nextTick 确保所有响应式数据都已初始化
  nextTick(() => {
    // 确保使用最新的 formData 值，包括从 startDate/endDate 获取日期
    const currentFormData = {
      stock_code: formData.value.stock_code || '',
      start_date: formData.value.start_date || startDate.value || '',
      end_date: formData.value.end_date || endDate.value || '',
      initial_capital: formData.value.initial_capital || 100000,
      strategy_type: formData.value.strategy_type || 'signal_based',
      shares_per_trade: formData.value.shares_per_trade || 100,
      hold_days: formData.value.hold_days || null,
      min_signal_strength: formData.value.min_signal_strength || signalStrength.value || 0.5,
      signal_types: formData.value.signal_types || []
    }
    console.log('[BacktestForm] Emitting initial formData:', currentFormData)
    emit('update:formData', currentFormData)
  })
})

// 监听日期变化，更新 formData
watch([startDate, endDate], ([newStart, newEnd], [oldStart, oldEnd]) => {
  console.log('[BacktestForm] Date watch triggered - startDate:', newStart, 'endDate:', newEnd, 'oldStart:', oldStart, 'oldEnd:', oldEnd)
  // 更新 formData 中的日期
  formData.value.start_date = newStart || ''
  formData.value.end_date = newEnd || ''
  console.log('[BacktestForm] Updated formData.start_date:', formData.value.start_date, 'formData.end_date:', formData.value.end_date)
  // 手动触发更新事件，确保父组件能立即获取到最新数据
  // 注意：formData 的深度 watch 也会触发，但手动触发更可靠
  emit('update:formData', { ...formData.value })
}, { immediate: false })

// 监听信号强度变化
watch(signalStrength, (newVal) => {
  formData.value.min_signal_strength = newVal
  emit('update:formData', { ...formData.value })
})

const formatSignalStrength = (val) => {
  return `${(val * 100).toFixed(0)}%`
}

// 监听整个 formData 对象的变化，确保所有字段变化都能被捕获（包括股票代码）
// 使用 deep 确保能捕获所有变化，但不使用 immediate，避免在初始化时清空数据
watch(() => formData.value, (newVal, oldVal) => {
  // 当 formData 的任何字段变化时，都触发更新事件
  // 避免重复触发（只在值真正变化时触发）
  const newStr = JSON.stringify(newVal)
  const oldStr = oldVal ? JSON.stringify(oldVal) : ''
  if (newStr !== oldStr) {
    console.log('[BacktestForm] formData deep watch triggered, emitting update:', newVal)
    console.log('[BacktestForm] formData deep watch - stock_code:', newVal.stock_code, 'start_date:', newVal.start_date, 'end_date:', newVal.end_date)
    emit('update:formData', { ...newVal })
  }
}, { deep: true, immediate: false, flush: 'post' })

// 注意：日期变化通过 watch([startDate, endDate]) 处理，不需要单独的处理函数

// 验证表单
const validate = () => {
  // 确保使用最新的数据（包括从 startDate/endDate 获取）
  const stockCode = formData.value.stock_code?.trim() || ''
  const startDateValue = formData.value.start_date || startDate.value || ''
  const endDateValue = formData.value.end_date || endDate.value || ''
  
  if (!stockCode) {
    return { valid: false, message: '请输入股票代码' }
  }
  if (!startDateValue || !endDateValue) {
    return { valid: false, message: '请选择回测期间' }
  }
  if (startDateValue > endDateValue) {
    return { valid: false, message: '开始日期不能晚于结束日期' }
  }
  if (formData.value.shares_per_trade % 100 !== 0) {
    return { valid: false, message: '每次交易股数必须是100的倍数' }
  }
  return { valid: true }
}

// 获取表单数据
const getFormData = () => {
  // 确保获取最新的数据，优先从响应式变量获取
  const stockCodeValue = formData.value.stock_code?.trim() || ''
  // 日期优先从 startDate/endDate 获取（因为它们是直接绑定到日期选择器的）
  const startDateValue = (startDate.value || formData.value.start_date || '').trim()
  const endDateValue = (endDate.value || formData.value.end_date || '').trim()
  
  // 如果日期选择器有值但 formData 中没有，同步更新
  if (startDate.value && !formData.value.start_date) {
    formData.value.start_date = startDate.value
  }
  if (endDate.value && !formData.value.end_date) {
    formData.value.end_date = endDate.value
  }
  
  const data = {
    stock_code: stockCodeValue,
    start_date: startDateValue,
    end_date: endDateValue,
    initial_capital: formData.value.initial_capital || 100000,
    strategy_type: formData.value.strategy_type || 'signal_based',
    shares_per_trade: formData.value.shares_per_trade || 100,
    hold_days: formData.value.hold_days || null,
    min_signal_strength: signalStrength.value || formData.value.min_signal_strength || 0.5,
    signal_types: Array.isArray(formData.value.signal_types) && formData.value.signal_types.length > 0
      ? formData.value.signal_types
      : null
  }
  
  console.log('[BacktestForm] getFormData - startDate.value:', startDate.value, 'type:', typeof startDate.value)
  console.log('[BacktestForm] getFormData - endDate.value:', endDate.value, 'type:', typeof endDate.value)
  console.log('[BacktestForm] getFormData - formData.value.start_date:', formData.value.start_date)
  console.log('[BacktestForm] getFormData - formData.value.end_date:', formData.value.end_date)
  console.log('[BacktestForm] getFormData result:', data)
  
  // 最终验证：确保日期不为空
  if (!data.start_date || !data.end_date) {
    console.warn('[BacktestForm] 警告：日期为空！startDate.value:', startDate.value, 'endDate.value:', endDate.value)
  }
  
  return data
}

// 重置表单
const reset = () => {
  formData.value = {
    stock_code: '',
    start_date: '',
    end_date: '',
    initial_capital: 100000,
    strategy_type: 'signal_based',
    shares_per_trade: 100,
    hold_days: null,
    min_signal_strength: 0.5,
    signal_types: []
  }
  startDate.value = ''
  endDate.value = ''
  signalStrength.value = 0.5
}

defineExpose({
  validate,
  getFormData,
  reset
})
</script>

<style scoped>
.backtest-form-container {
  padding: 12px 16px;
  background: #f9f9f9;
  border-radius: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.backtest-form-container :deep(.el-form) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: flex-start;
}

.backtest-form-container :deep(.el-form-item) {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.backtest-form-container :deep(.el-form-item__label) {
  font-size: 12px;
  color: #2d3748;
  font-weight: 500;
  padding-right: 8px;
  line-height: 1.5;
}

.backtest-form-container :deep(.el-form-item__content) {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.signal-strength-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 滚动条样式 */
.backtest-form-container::-webkit-scrollbar {
  width: 6px;
}

.backtest-form-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.backtest-form-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.backtest-form-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>

