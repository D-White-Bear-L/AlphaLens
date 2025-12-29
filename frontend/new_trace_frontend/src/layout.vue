<template>
    <div class="common-layout" :class="{ 'is-collapsed': isSidebarCollapsed }">
      <el-container>
        <el-aside :width="sidebarWidth">
          <SideBar @collapse-change="handleCollapseChange" @load-history="handleLoadHistory" />
        </el-aside>
        <el-container class="main-container">
          <el-header class="header">
            <HeaderBar />
          </el-header>
          <el-main>
            <router-view ref="routerView" />
          </el-main>
        </el-container>
      </el-container>
    </div>
</template>

<script>
import SideBar from '@/components/sidebar.vue'
import HeaderBar from '@/components/header.vue'
import { ref, computed } from 'vue'

export default {
    name: 'CommonLayout',
    components: {
        SideBar,
        HeaderBar
    },
    setup() {
        const isSidebarCollapsed = ref(false)
        const routerView = ref(null)
        
        const sidebarWidth = computed(() => {
            return isSidebarCollapsed.value ? '64px' : '260px'
        })
        
        const handleCollapseChange = (collapsed) => {
            isSidebarCollapsed.value = collapsed
        }

        const handleLoadHistory = (history) => {
            // 使用事件总线或直接调用组件方法
            // 由于 Vue 3 的 setup 语法，我们需要通过 provide/inject 或者事件总线
            // 这里使用简单的方式：通过 window 事件（临时方案）
            window.dispatchEvent(new CustomEvent('load-chat-history', { detail: history }))
        }
        
        return {
            isSidebarCollapsed,
            sidebarWidth,
            routerView,
            handleCollapseChange,
            handleLoadHistory
        }
    }
}
</script>

<style>
.common-layout {
    min-height: 100vh;
    background-color: #ffffff;
}

.common-layout .el-aside {
    position: relative;
    z-index: 2;
    transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    background-color: #f7f7f8;
}

.common-layout .main-container {
    flex: 1;
    transition: margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    width: calc(100% - 260px);
    margin-left: 0;
}

.common-layout.is-collapsed .main-container {
    width: calc(100% - 64px);
}

.common-layout .el-header {
    height: 60px;
    border-bottom: 1px solid #e5e7eb;
    box-sizing: border-box;
    background-color: #ffffff;
    position: relative;
    z-index: 1;
    padding: 0 24px;
    display: flex;
    align-items: center;
}

.common-layout .el-main {
    margin: 0;
    background-color: #ffffff;
    position: relative;
    z-index: 0;
    overflow: hidden;
    padding: 0;
    height: calc(100vh - 60px);
}

/* 移除这个选择器，使用上面的新选择器 */
/* .common-layout .is-sidebar-collapsed {
    margin-left: 64px;
} */
</style>