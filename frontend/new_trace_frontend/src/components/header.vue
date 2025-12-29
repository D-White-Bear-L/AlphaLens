<template>
    <div class="header-container">
        <!-- 左侧区域 -->
        <div class="header-left">
            <div class="breadcrumb">
                <el-breadcrumb separator="/">
                    <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
                    <el-breadcrumb-item v-if="currentRoute">{{ currentRouteName }}</el-breadcrumb-item>
                </el-breadcrumb>
            </div>
        </div>
    
        
        <!-- 右侧区域 -->
        <div class="header-right">
            <!-- 通知图标 -->
            <!-- <el-badge :value="notificationCount" class="notification-badge">
                <el-icon class="header-icon"><Bell /></el-icon>
            </el-badge> -->
            
            <!-- 全屏按钮 -->
            <el-tooltip content="全屏显示" placement="bottom">
                <el-icon class="header-icon" @click="toggleFullScreen">
                    <FullScreen />
                </el-icon>
            </el-tooltip>
            
            <!-- 用户信息 -->
            <el-dropdown trigger="click">
                <div class="user-info">
                    <el-avatar :size="32" :src="userInfo.avatarUrl || defaultAvatar" />
                    <!-- <span class="username">{{ name }}</span> -->
                     <span class="username">WhiteBear</span>
                </div>
                <template #dropdown>
                    <el-dropdown-menu>
                        <el-dropdown-item @click="navigateTo('/user')">个人信息</el-dropdown-item>
                        <!-- <el-dropdown-item @click="navigateTo('/settings')">系统设置</el-dropdown-item> -->
                        <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
                    </el-dropdown-menu>
                </template>
            </el-dropdown>
        </div>
    </div>
</template>

<script>
// Bell,
import { ref, computed, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FullScreen } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
// import { logout as logoutApi } from '@/api/login/login'
// import { fetchUserInfo } from '../api/UserSetting'
// import { getUserInfo as fetchUserInfo } from '../api/UserSetting'

export default {
    name: 'HeaderBar',
    components: {
        // Bell,
        FullScreen
    },
    setup() {
        const defaultAvatar = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'
        const userInfo = reactive({
            avatarUrl: '',
            username: ''
        })
        
        // 从 localStorage 获取用户信息
        const getUserInfo = () => {
            try {
                const storedUserInfo = localStorage.getItem('userInfo')
                if (storedUserInfo) {
                    const parsed = JSON.parse(storedUserInfo)
                    userInfo.username = parsed.username || parsed.name || '用户'
                    userInfo.avatarUrl = parsed.avatarUrl || ''
                } else {
                    userInfo.username = '用户'
                }
            } catch (error) {
                console.error('获取用户信息失败:', error)
                userInfo.username = '用户'
            }
        }

        const searchText = ref('')
        const notificationCount = ref(5)
        const route = useRoute()
        const router = useRouter()
        
        const navigateTo = (path) => {
            router.push(path)
        }
        
        const logout = () => {
            // 清除本地存储
            localStorage.removeItem('token')
            localStorage.removeItem('userInfo')
            ElMessage.success('已退出')
            // 如果需要跳转，可以取消下面的注释
            // router.push('/login')
        }
        
        const currentRouteName = computed(() => {
            return route.meta.title || route.name || ''
        })
        
        const currentRoute = computed(() => {
            return route.path !== '/'
        })
        
        // 全屏切换功能
        const toggleFullScreen = () => {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen()
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen()
                }
            }
        }
        
        onMounted(() => {
            getUserInfo()
        })

        return {
            searchText,
            notificationCount,
            currentRouteName,
            currentRoute,
            toggleFullScreen,
            navigateTo,
            logout,
            userInfo,
            defaultAvatar,
            name: computed(() => userInfo.username)
        }
    }
}
</script>

<style scoped>
.header-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 100%;
    width: 100%;
}

.header-left, .header-center, .header-right {
    display: flex;
    align-items: center;
}

.header-left {
    flex: 1;
}

.header-center {
    flex: 2;
    justify-content: center;
}

.header-right {
    flex: 1;
    justify-content: flex-end;
    gap: 16px;
}

.search-input {
    max-width: 300px;
}

.header-icon {
    font-size: 20px;
    cursor: pointer;
    color: #606266;
}

.header-icon:hover {
    color: #409EFF;
}

.notification-badge {
    margin-right: 8px;
}

.user-info {
    display: flex;
    align-items: center;
    cursor: pointer;
}

.username {
    margin-left: 8px;
    font-size: 14px;
    color: #606266;
}

.breadcrumb {
    font-size: 14px;
}
</style>