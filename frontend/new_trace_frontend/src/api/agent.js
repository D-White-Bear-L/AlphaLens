import request from '@/utils/request'

/**
 * 新闻溯源 API（同步，向后兼容）
 * @param {Object} data - 请求数据
 * @param {string} data.claim - 要溯源的声明
 * @returns {Promise}
 */
export const traceNews = (data) => {
  return request({
    url: '/api/v1/trace',
    method: 'post',
    data,
    timeout: 300000 // 5分钟超时（仅作为最后保障）
  })
}

/**
 * 创建异步新闻溯源任务
 * @param {Object} data - 请求数据
 * @param {string} data.claim - 要溯源的声明
 * @returns {Promise} 返回任务状态，包含 task_id
 */
export const traceNewsAsync = (data) => {
  return request({
    url: '/api/v1/trace/async',
    method: 'post',
    data
  })
}

/**
 * 查询任务状态
 * @param {string} taskId - 任务ID
 * @returns {Promise} 返回任务状态
 */
export const getTaskStatus = (taskId) => {
  return request({
    url: `/api/v1/trace/status/${taskId}`,
    method: 'get'
  })
}

/**
 * 取消任务
 * @param {string} taskId - 任务ID
 * @returns {Promise} 返回任务状态
 */
export const cancelTask = (taskId) => {
  return request({
    url: `/api/v1/trace/cancel/${taskId}`,
    method: 'post'
  })
}

/**
 * 获取健康状态
 * @returns {Promise}
 */
export const healthCheck = () => {
  return request({
    url: '/api/v1/health',
    method: 'get'
  })
}

// ==================== 金融分析 API ====================

/**
 * 创建异步金融分析任务
 * @param {Object} data - 请求数据
 * @param {string} data.stock_code - 股票代码 (e.g., '000001')
 * @param {string} data.start_date - 开始日期 (格式: 'YYYYMMDD')
 * @param {string} data.end_date - 结束日期 (格式: 'YYYYMMDD')
 * @returns {Promise} 返回任务状态，包含 task_id
 */
export const analyzeStockAsync = (data) => {
  return request({
    url: '/api/v1/financial/analyze/async',
    method: 'post',
    data
  })
}

/**
 * 查询金融分析任务状态
 * @param {string} taskId - 任务ID
 * @returns {Promise} 返回任务状态
 */
export const getFinancialTaskStatus = (taskId) => {
  return request({
    url: `/api/v1/financial/status/${taskId}`,
    method: 'get'
  })
}

/**
 * 取消金融分析任务
 * @param {string} taskId - 任务ID
 * @returns {Promise} 返回任务状态
 */
export const cancelFinancialTask = (taskId) => {
  return request({
    url: `/api/v1/financial/cancel/${taskId}`,
    method: 'post'
  })
}

/**
 * 股票推荐（同步，向后兼容）
 * @param {Object} data - 请求数据
 * @param {Array<string>} data.stock_codes - 指定股票代码列表（可选，如果为null则获取热门股票）
 * @param {number} data.max_stocks - 最大分析股票数（1-50，默认10）
 * @param {string} data.start_date - 开始日期 (格式: 'YYYYMMDD')
 * @param {string} data.end_date - 结束日期 (格式: 'YYYYMMDD')
 * @param {number} data.min_recommendation_score - 最低推荐分数（0-1，默认0.5）
 * @param {string} data.focus_sector - 行业筛选（可选，如'科技', '金融', '消费'）
 * @returns {Promise} 返回股票推荐结果
 */
export const recommendStocks = (data) => {
  return request({
    url: '/api/v1/financial/recommend',
    method: 'post',
    data,
    timeout: 300000 // 5分钟超时
  })
}

/**
 * 创建异步股票推荐任务
 * @param {Object} data - 请求数据
 * @param {Array<string>} data.stock_codes - 指定股票代码列表（可选，如果为null则获取热门股票）
 * @param {number} data.max_stocks - 最大分析股票数（1-50，默认10）
 * @param {string} data.start_date - 开始日期 (格式: 'YYYYMMDD')
 * @param {string} data.end_date - 结束日期 (格式: 'YYYYMMDD')
 * @param {number} data.min_recommendation_score - 最低推荐分数（0-1，默认0.5）
 * @param {string} data.focus_sector - 行业筛选（可选，如'科技', '金融', '消费'）
 * @returns {Promise} 返回任务状态，包含 task_id
 */
export const recommendStocksAsync = (data) => {
  return request({
    url: '/api/v1/financial/recommend/async',
    method: 'post',
    data
  })
}

/**
 * 查询股票推荐任务状态
 * @param {string} taskId - 任务ID
 * @returns {Promise} 返回任务状态
 */
export const getRecommendationTaskStatus = (taskId) => {
  return request({
    url: `/api/v1/financial/recommend/status/${taskId}`,
    method: 'get'
  })
}

/**
 * 取消股票推荐任务
 * @param {string} taskId - 任务ID
 * @returns {Promise} 返回任务状态
 */
export const cancelRecommendationTask = (taskId) => {
  return request({
    url: `/api/v1/financial/recommend/cancel/${taskId}`,
    method: 'post'
  })
}

/**
 * 策略回测
 * @param {Object} data - 回测请求数据
 * @param {string} data.stock_code - 股票代码
 * @param {string} data.start_date - 开始日期 (格式: 'YYYYMMDD')
 * @param {string} data.end_date - 结束日期 (格式: 'YYYYMMDD')
 * @param {number} data.initial_capital - 初始资金（默认100000）
 * @param {string} data.strategy_type - 策略类型（默认'signal_based'）
 * @param {number} data.shares_per_trade - 每次交易股数（默认100）
 * @param {number} data.hold_days - 持有天数（可选）
 * @param {number} data.min_signal_strength - 最小信号强度（默认0.5）
 * @param {Array<string>} data.signal_types - 信号类型列表（可选）
 * @returns {Promise} 返回回测结果
 */
export const backtestStrategy = (data) => {
  return request({
    url: '/api/v1/financial/backtest',
    method: 'post',
    data,
    timeout: 300000 // 5分钟超时
  })
}

// ==================== 股票预测 API ====================

/**
 * 股票价格预测（同步）
 * @param {Object} data - 预测请求数据
 * @param {string} data.stock_code - 股票代码
 * @param {string} data.start_date - 训练数据开始日期 (格式: 'YYYYMMDD')
 * @param {string} data.end_date - 训练数据结束日期 (格式: 'YYYYMMDD')
 * @param {number} data.prediction_days - 预测天数（1-30，默认5）
 * @param {string} data.model_type - 模型类型（linear, ridge, lasso, random_forest, gradient_boosting, ensemble）
 * @param {boolean} data.use_technical_indicators - 是否使用技术指标（默认true）
 * @returns {Promise} 返回预测结果
 */
export const predictStockPrice = (data) => {
  return request({
    url: '/api/v1/financial/predict',
    method: 'post',
    data,
    timeout: 300000 // 5分钟超时
  })
}

/**
 * 创建异步股票预测任务
 * @param {Object} data - 预测请求数据
 * @param {string} data.stock_code - 股票代码
 * @param {string} data.start_date - 训练数据开始日期 (格式: 'YYYYMMDD')
 * @param {string} data.end_date - 训练数据结束日期 (格式: 'YYYYMMDD')
 * @param {number} data.prediction_days - 预测天数（1-30，默认5）
 * @param {string} data.model_type - 模型类型
 * @param {boolean} data.use_technical_indicators - 是否使用技术指标
 * @returns {Promise} 返回任务状态，包含 task_id
 */
export const predictStockPriceAsync = (data) => {
  return request({
    url: '/api/v1/financial/predict/async',
    method: 'post',
    data
  })
}

/**
 * 查询股票预测任务状态
 * @param {string} taskId - 任务ID
 * @returns {Promise} 返回任务状态
 */
export const getPredictionTaskStatus = (taskId) => {
  return request({
    url: `/api/v1/financial/predict/status/${taskId}`,
    method: 'get'
  })
}

/**
 * 取消股票预测任务
 * @param {string} taskId - 任务ID
 * @returns {Promise} 返回任务状态
 */
export const cancelPredictionTask = (taskId) => {
  return request({
    url: `/api/v1/financial/predict/cancel/${taskId}`,
    method: 'post'
  })
}

