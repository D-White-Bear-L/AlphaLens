<template>
    <div class="sidebar-container">
        <!-- 顶部 Logo 和标题 -->
        <div class="sidebar-header">
            <div class="logo-section">
                <div class="logo">
                    <img src="/logo.jpg" alt="Logo" />
                </div>
                <span class="app-name">AlphaLens</span>
            </div>
        </div>

        <!-- 工具区域 -->
        <div class="tools-section">
            <div class="tool-item" @click="handleNewChat">
                <el-icon><Plus /></el-icon>
                <span>新对话</span>
            </div>
            <div class="tool-item" @click="handleSearchChat">
                <el-icon><Search /></el-icon>
                <span>搜索对话</span>
            </div>
        </div>

        <!-- 对话历史区域 -->
        <div class="history-section">
            <div class="history-title">你的对话</div>
            <div class="history-list">
                <div v-if="histories.length === 0" class="empty-history">
                    <p>暂无对话记录</p>
                </div>
                <div 
                    v-for="history in histories" 
                    :key="history.chatId || history.agentId"
                    class="history-item"
                    :class="{ 'active': activeHistoryId === (history.chatId || history.agentId) }"
                    @click="loadHistory(history)"
                >
                    <div class="history-icon">
                        <el-icon>
                            <component :is="getHistoryIcon(history)" />
                        </el-icon>
                    </div>
                    <div class="history-content">
                        <div class="history-title-text">{{ getHistoryTitle(history) }}</div>
                    </div>
                    <el-button 
                        type="danger" 
                        :icon="Delete" 
                        size="small" 
                        text
                        @click.stop="deleteHistory(history.chatId || history.agentId)"
                        class="delete-btn"
                    />
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Delete, Document, ChatDotRound, DataAnalysis } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAllChatHistories, deleteChatHistory } from '@/utils/chatHistory'

export default {
    name: 'SideBar',
    components: {
        Plus,
        Search,
        Delete,
        Document,
        ChatDotRound,
        DataAnalysis
    },
    emits: ['new-chat', 'load-history'],
    setup(props, { emit }) {
        const router = useRouter()
        const histories = ref([])
        const activeHistoryId = ref(null)
        
        const handleNewChat = () => {
            activeHistoryId.value = null
            emit('new-chat')
            // 触发事件让 ChatView 清空并重置
            window.dispatchEvent(new CustomEvent('new-chat'))
        }

        const handleSearchChat = () => {
            ElMessage.info('搜索功能开发中')
        }

        const loadHistories = () => {
            histories.value = getAllChatHistories()
        }

        const loadHistory = (history) => {
            // 使用 chatId 或 agentId 作为唯一标识
            const chatId = history.chatId || history.agentId
            activeHistoryId.value = chatId
            window.dispatchEvent(new CustomEvent('load-chat-history', { 
                detail: { 
                    chatId: chatId,
                    agentId: history.agentId // 保持向后兼容
                } 
            }))
        }

        const deleteHistory = async (chatId) => {
            try {
                await ElMessageBox.confirm(
                    '确定要删除这条对话记录吗？',
                    '提示',
                    {
                        confirmButtonText: '确定',
                        cancelButtonText: '取消',
                        type: 'warning'
                    }
                )
                deleteChatHistory(chatId)
                if (activeHistoryId.value === chatId) {
                    activeHistoryId.value = null
                }
                loadHistories()
                ElMessage.success('删除成功')
            } catch {
                // 用户取消
            }
        }

        const getHistoryTitle = (history) => {
            // 从第一条用户消息中获取标题
            // 注意：history 可能是从 getAllChatHistories 返回的，它包含 preview 字段
            if (history.preview) {
                return history.preview.length > 30 ? history.preview.substring(0, 30) + '...' : history.preview
            }
            if (history.messages && history.messages.length > 0) {
                const firstUserMessage = history.messages.find(m => m.role === 'user')
                if (firstUserMessage && firstUserMessage.content) {
                    const title = firstUserMessage.content.substring(0, 30)
                    return title.length < firstUserMessage.content.length ? title + '...' : title
                }
            }
            return history.agent?.name || '新对话'
        }

        const getHistoryIcon = (history) => {
            // iconComponent 无法序列化到 localStorage，所以总是根据 agent.id 选择图标
            // 确保 history 和 agent 存在
            if (!history || !history.agent) {
                return ChatDotRound
            }
            // 根据 agent.id 选择图标
            const agentId = history.agent.id
            if (agentId === 'news_trace') {
                return Search
            } else if (agentId === 'finance_quant') {
                return DataAnalysis
            }
            // 默认使用聊天图标
            return ChatDotRound
        }

        onMounted(() => {
            loadHistories()
            // 监听 storage 变化（其他窗口/标签页修改时）
            window.addEventListener('storage', loadHistories)
            // 监听自定义事件（当前窗口内修改时）
            window.addEventListener('chat-history-updated', loadHistories)
        })

        onUnmounted(() => {
            // 组件卸载时移除事件监听
            window.removeEventListener('storage', loadHistories)
            window.removeEventListener('chat-history-updated', loadHistories)
        })

        return {
            histories,
            activeHistoryId,
            handleNewChat,
            handleSearchChat,
            loadHistory,
            deleteHistory,
            getHistoryTitle,
            getHistoryIcon,
            loadHistories,
            Delete,
            Search,
            ChatDotRound,
            DataAnalysis
        }
    }
}
</script>

<style scoped>
.sidebar-container {
    height: 100vh;
    background-color: #f7f7f8;
    display: flex;
    flex-direction: column;
    border-right: 1px solid #e5e5e6;
}

.sidebar-header {
    padding: 16px;
    border-bottom: 1px solid #e5e5e6;
}

.logo-section {
    display: flex;
    align-items: center;
    gap: 10px;
}

.logo {
    width: 32px;
    height: 32px;
    border-radius: 6px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.logo img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.app-name {
    font-size: 16px;
    font-weight: 600;
    color: #2d3748;
}

.tools-section {
    padding: 8px;
    border-bottom: 1px solid #e5e5e6;
}

.tool-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.2s;
    color: #4a5568;
    font-size: 14px;
}

.tool-item:hover {
    background-color: #e5e7eb;
}

.tool-item .el-icon {
    font-size: 18px;
}

.history-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 8px;
}

.history-title {
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.history-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.empty-history {
    text-align: center;
    padding: 40px 20px;
    color: #9ca3af;
    font-size: 14px;
}

.history-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
    color: #4a5568;
}

.history-item:hover {
    background-color: #e5e7eb;
}

.history-item.active {
    background-color: #e5e7eb;
}

.history-icon {
    font-size: 16px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #667eea;
}

.history-icon .el-icon {
    font-size: 18px;
}

.history-content {
    flex: 1;
    min-width: 0;
}

.history-title-text {
    font-size: 14px;
    color: #2d3748;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.delete-btn {
    opacity: 0;
    transition: opacity 0.2s;
    flex-shrink: 0;
}

.history-item:hover .delete-btn {
    opacity: 1;
}
</style>
