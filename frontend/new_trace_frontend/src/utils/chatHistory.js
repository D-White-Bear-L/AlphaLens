/**
 * 对话历史管理工具
 * 使用 localStorage 存储对话历史
 */

const STORAGE_PREFIX = 'chat_history_'
const MAX_HISTORY_COUNT = 50 // 每个 agent 最多保存的历史记录数

/**
 * 生成唯一的对话 ID
 * @param {string} agentId - Agent ID
 * @returns {string} 唯一的对话 ID
 */
export const generateChatId = (agentId) => {
  const timestamp = Date.now()
  const random = Math.random().toString(36).substring(2, 9)
  return `${agentId}_${timestamp}_${random}`
}

/**
 * 保存对话历史
 * @param {string} chatId - 对话 ID（如果不存在则自动生成）
 * @param {Object} chatData - 对话数据 { agent, messages, chatId? }
 * @returns {string} 返回使用的 chatId
 */
export const saveChatHistory = (chatId, chatData) => {
  try {
    // 如果没有提供 chatId，则生成一个
    let finalChatId = chatId
    if (!finalChatId && chatData.agent) {
      finalChatId = generateChatId(chatData.agent.id)
    }
    
    if (!finalChatId) {
      console.error('无法保存对话历史：缺少 chatId 或 agent')
      return null
    }
    
    const key = `${STORAGE_PREFIX}${finalChatId}`
    const history = {
      chatId: finalChatId,
      agent: chatData.agent,
      messages: chatData.messages,
      lastUpdate: new Date().toISOString()
    }
    localStorage.setItem(key, JSON.stringify(history))
    return finalChatId
  } catch (error) {
    console.error('保存对话历史失败:', error)
    return null
  }
}

/**
 * 获取对话历史
 * @param {string} chatId - 对话 ID
 * @returns {Object|null} 对话历史数据
 */
export const getChatHistory = (chatId) => {
  try {
    const key = `${STORAGE_PREFIX}${chatId}`
    const data = localStorage.getItem(key)
    if (data) {
      return JSON.parse(data)
    }
    return null
  } catch (error) {
    console.error('获取对话历史失败:', error)
    return null
  }
}

/**
 * 获取所有对话历史列表
 * @returns {Array} 所有对话历史列表
 */
export const getAllChatHistories = () => {
  const histories = []
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.startsWith(STORAGE_PREFIX)) {
        const agentId = key.replace(STORAGE_PREFIX, '')
        const data = localStorage.getItem(key)
        if (data) {
          try {
            const history = JSON.parse(data)
            // 从第一条用户消息获取预览
            let preview = ''
            if (history.messages && history.messages.length > 0) {
              const firstUserMessage = history.messages.find(m => m.role === 'user')
              if (firstUserMessage && firstUserMessage.content) {
                preview = firstUserMessage.content.substring(0, 50)
              }
            }
            
            histories.push({
              agentId: history.chatId || agentId, // 使用 chatId 如果存在，否则使用旧的 agentId
              chatId: history.chatId || agentId,
              agent: history.agent,
              messageCount: history.messages ? history.messages.length : 0,
              lastUpdate: history.lastUpdate,
              preview: preview
            })
          } catch (e) {
            console.error('解析历史记录失败:', key, e)
          }
        }
      }
    }
    // 按最后更新时间排序
    histories.sort((a, b) => {
      return new Date(b.lastUpdate) - new Date(a.lastUpdate)
    })
  } catch (error) {
    console.error('获取所有对话历史失败:', error)
  }
  return histories
}

/**
 * 删除对话历史
 * @param {string} chatId - 对话 ID
 */
export const deleteChatHistory = (chatId) => {
  try {
    const key = `${STORAGE_PREFIX}${chatId}`
    localStorage.removeItem(key)
  } catch (error) {
    console.error('删除对话历史失败:', error)
  }
}

/**
 * 清空所有对话历史
 */
export const clearAllChatHistories = () => {
  try {
    const keysToRemove = []
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.startsWith(STORAGE_PREFIX)) {
        keysToRemove.push(key)
      }
    }
    keysToRemove.forEach(key => localStorage.removeItem(key))
  } catch (error) {
    console.error('清空所有对话历史失败:', error)
  }
}

