<template>
  <div class="prediction-form-container">
    <el-form :model="formData" label-width="100px" size="small" :inline="true">
      <el-form-item label="股票代码" required>
        <el-input 
          v-model="formData.stock_code" 
          placeholder="如: 000001"
          style="width: 120px"
          :disabled="loading"
        />
      </el-form-item>
      
      <el-form-item label="训练期间" required>
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
      
      <el-form-item label="预测天数">
        <el-input-number
          v-model="formData.prediction_days"
          :min="1"
          :max="30"
          :step="1"
          :precision="0"
          style="width: 100px"
          :disabled="loading"
        />
        <span style="margin-left: 6px; color: #666; font-size: 12px;">天</span>
      </el-form-item>
      
      <el-form-item label="模型类型">
        <el-select 
          v-model="formData.model_type" 
          style="width: 150px"
          :disabled="loading"
        >
          <el-option label="线性回归" value="linear" />
          <el-option label="Ridge回归" value="ridge" />
          <el-option label="Lasso回归" value="lasso" />
          <el-option label="随机森林" value="random_forest" />
          <el-option label="梯度提升" value="gradient_boosting" />
          <el-option label="集成模型" value="ensemble" />
        </el-select>
      </el-form-item>
      
      <el-form-item label="技术指标">
        <el-switch
          v-model="formData.use_technical_indicators"
          :disabled="loading"
        />
        <span style="margin-left: 6px; color: #999; font-size: 11px;">使用技术指标作为特征</span>
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

const formData = ref({
  stock_code: '',
  start_date: '',
  end_date: '',
  prediction_days: 5,
  model_type: 'ensemble',
  use_technical_indicators: true
})

// 组件挂载时立即触发一次更新事件
onMounted(() => {
  nextTick(() => {
    const currentFormData = {
      stock_code: formData.value.stock_code || '',
      start_date: formData.value.start_date || startDate.value || '',
      end_date: formData.value.end_date || endDate.value || '',
      prediction_days: formData.value.prediction_days || 5,
      model_type: formData.value.model_type || 'ensemble',
      use_technical_indicators: formData.value.use_technical_indicators !== false
    }
    emit('update:formData', currentFormData)
  })
})

// 监听日期变化
watch([startDate, endDate], ([newStart, newEnd]) => {
  formData.value.start_date = newStart || ''
  formData.value.end_date = newEnd || ''
  emit('update:formData', { ...formData.value })
}, { immediate: false })

// 监听整个 formData 对象的变化
watch(() => formData.value, (newVal, oldVal) => {
  if (JSON.stringify(newVal) !== JSON.stringify(oldVal)) {
    emit('update:formData', { ...newVal })
  }
}, { deep: true, immediate: false })

// 验证表单
const validate = () => {
  const stockCode = formData.value.stock_code?.trim() || ''
  const startDateValue = formData.value.start_date || startDate.value || ''
  const endDateValue = formData.value.end_date || endDate.value || ''
  
  if (!stockCode) {
    return { valid: false, message: '请输入股票代码' }
  }
  if (!startDateValue || !endDateValue) {
    return { valid: false, message: '请选择训练期间' }
  }
  if (startDateValue > endDateValue) {
    return { valid: false, message: '开始日期不能晚于结束日期' }
  }
  return { valid: true }
}

// 获取表单数据
const getFormData = () => {
  const stockCodeValue = formData.value.stock_code?.trim() || ''
  const startDateValue = (startDate.value || formData.value.start_date || '').trim()
  const endDateValue = (endDate.value || formData.value.end_date || '').trim()
  
  if (startDate.value && !formData.value.start_date) {
    formData.value.start_date = startDate.value
  }
  if (endDate.value && !formData.value.end_date) {
    formData.value.end_date = endDate.value
  }
  
  return {
    stock_code: stockCodeValue,
    start_date: startDateValue,
    end_date: endDateValue,
    prediction_days: formData.value.prediction_days || 5,
    model_type: formData.value.model_type || 'ensemble',
    use_technical_indicators: formData.value.use_technical_indicators !== false
  }
}

// 重置表单
const reset = () => {
  formData.value = {
    stock_code: '',
    start_date: '',
    end_date: '',
    prediction_days: 5,
    model_type: 'ensemble',
    use_technical_indicators: true
  }
  startDate.value = ''
  endDate.value = ''
}

defineExpose({
  validate,
  getFormData,
  reset
})
</script>

<style scoped>
.prediction-form-container {
  padding: 12px 16px;
  background: #f9f9f9;
  border-radius: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.prediction-form-container :deep(.el-form) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: flex-start;
}

.prediction-form-container :deep(.el-form-item) {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.prediction-form-container :deep(.el-form-item__label) {
  font-size: 12px;
  color: #2d3748;
  font-weight: 500;
  padding-right: 8px;
  line-height: 1.5;
}

.prediction-form-container :deep(.el-form-item__content) {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

/* 滚动条样式 */
.prediction-form-container::-webkit-scrollbar {
  width: 6px;
}

.prediction-form-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.prediction-form-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.prediction-form-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>

