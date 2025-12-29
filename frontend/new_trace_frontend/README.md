# 新闻溯源前端应用 (News Trace Frontend)

一个基于 Vue 3 的现代化新闻溯源前端应用，提供直观的数据可视化和交互式界面。

## 📋 项目简介

本项目是一个新闻溯源系统的前端应用，主要用于展示新闻溯源结果，包括来源分析、时间线、因果关系、知识图谱和层次结构等多种维度的可视化展示。

## 🛠️ 技术栈

### 核心框架
- **Vue 3.5.24** - 渐进式 JavaScript 框架，采用 Composition API
- **Vite 7.2.4** - 下一代前端构建工具，提供极速的开发体验和热更新

### UI 框架
- **Element Plus 2.12.0** - 基于 Vue 3 的企业级 UI 组件库
- **@element-plus/icons-vue 2.3.2** - Element Plus 官方图标库

### 路由管理
- **Vue Router 4.6.4** - Vue.js 官方路由管理器，支持 HTML5 History 模式

### HTTP 客户端
- **Axios 1.13.2** - 基于 Promise 的 HTTP 客户端，用于与后端 API 通信

### 数据可视化
- **vis-network** (CDN) - 强大的网络图谱可视化库，用于渲染知识图谱和层次结构图

### 开发工具
- **@vitejs/plugin-vue 6.0.1** - Vite 的 Vue 单文件组件支持插件

## 📁 项目结构

```
new_trace_frontend/
├── src/
│   ├── api/                    # API 接口定义
│   │   └── agent.js           # 新闻溯源相关 API
│   ├── assets/                 # 静态资源
│   ├── components/             # 公共组件
│   │   ├── NewsTraceResult.vue # 溯源结果展示组件（核心）
│   │   ├── header.vue         # 顶部导航栏
│   │   └── sidebar.vue        # 侧边栏
│   ├── router/                 # 路由配置
│   │   └── index.js           # 路由定义
│   ├── utils/                  # 工具函数
│   │   ├── request.js         # Axios 封装和拦截器
│   │   └── chatHistory.js     # 聊天历史管理
│   ├── views/                  # 页面视图
│   │   ├── Chat/              # 聊天视图
│   │   │   └── ChatView.vue
│   │   └── newTrace/          # 新闻溯源视图
│   │       └── newTrace.vue
│   ├── App.vue                 # 根组件
│   ├── layout.vue              # 布局组件
│   ├── main.js                 # 应用入口
│   └── style.css               # 全局样式
├── public/                     # 公共静态文件
├── index.html                  # HTML 模板
├── vite.config.js              # Vite 配置文件
└── package.json                # 项目依赖配置
```

## 🎨 核心功能实现分析

### 1. 组件化架构设计

项目采用组件化开发模式，主要组件包括：

#### NewsTraceResult.vue (核心组件)
- **功能**: 展示新闻溯源的完整结果
- **特性**:
  - 多标签页展示（来源列表、时间线、因果关系、知识图谱、层次结构、深度分析）
  - 使用 Vue 3 Composition API (`<script setup>`) 实现响应式逻辑
  - 动态加载 vis-network 库进行图谱可视化
  - 支持图谱/列表视图切换

#### 布局组件
- **layout.vue**: 提供侧边栏和顶部导航的通用布局
- **sidebar.vue**: 侧边栏，支持折叠/展开，管理聊天历史
- **header.vue**: 顶部导航栏

### 2. 数据可视化实现

#### 知识图谱可视化
- **技术**: vis-network 库
- **实现**:
  ```javascript
  // 动态加载 vis-network CDN
  const script = document.createElement('script')
  script.src = 'https://unpkg.com/vis-network/standalone/umd/vis-network.min.js'
  
  // 使用物理引擎布局（Barnes-Hut 算法）
  physics: {
    enabled: true,
    barnesHut: {
      gravitationalConstant: -2000,
      centralGravity: 0.3,
      springLength: 200
    }
  }
  ```
- **特点**:
  - 支持节点类型颜色区分（人物、组织、地点、概念、事件）
  - 可交互式操作（拖拽、缩放、悬停提示）
  - 支持中文字体渲染

#### 层次结构可视化
- **布局**: 层次布局（Hierarchical Layout）
- **方向**: 从上到下（UD）
- **特点**:
  - 根据层级设置不同颜色
  - 支持节点标签自动换行
  - 自适应节点宽度和高度
  - 根节点特殊样式（更大字体、更粗边框）

### 3. 状态管理

#### 响应式数据
使用 Vue 3 的 `ref` 和 `computed` 实现响应式数据管理：

```javascript
// 标签页状态
const activeTab = ref('sources')
const kgView = ref('graph')
const hierarchyView = ref('tree')

// 计算属性
const sources = computed(() => props.result.sources || [])
const confidence = computed(() => props.result.confidence || 0)
```

#### 组件通信
- **Props**: 父子组件数据传递
- **Events**: 子组件向父组件发送事件
- **Provide/Inject**: 跨层级组件通信（可选）

### 4. API 封装与错误处理

#### 请求封装 (`utils/request.js`)
- **特点**:
  - 统一的 Axios 实例配置
  - 请求/响应拦截器
  - 自动 Token 注入
  - 统一错误处理
  - 环境区分（开发/生产）

```javascript
// 开发环境使用 Vite 代理
baseURL: import.meta.env.DEV ? '' : 'http://0.0.0.0:8000'

// Vite 代理配置（vite.config.js）
proxy: {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true
  }
}
```

#### API 接口 (`api/agent.js`)
- **同步接口**: `traceNews()` - 同步新闻溯源（5分钟超时）
- **异步接口**: 
  - `traceNewsAsync()` - 创建异步任务
  - `getTaskStatus()` - 查询任务状态
  - `cancelTask()` - 取消任务
- **工具接口**: `healthCheck()` - 健康检查

### 5. 路由管理

使用 Vue Router 4 实现单页面应用路由：

```javascript
// 路由配置（router/index.js）
const routes = [
  {
    path: '/',
    component: LayOut,
    redirect: '/chat',
    children: [
      { 
        path: 'chat', 
        name: 'Chat', 
        component: () => import('@/views/Chat/ChatView.vue')
      }
    ]
  }
]
```

- **模式**: HTML5 History 模式
- **懒加载**: 使用动态 `import()` 实现路由组件懒加载

### 6. 样式设计

#### CSS 架构
- **全局样式**: `style.css` 和 `App.vue` 中的全局重置
- **组件样式**: 使用 `<style scoped>` 实现样式隔离
- **响应式设计**: 使用 Flexbox 和 Grid 布局

#### 主题色彩
- **置信度标签**: 高（绿色）、中（黄色）、低（红色）
- **图谱节点**: 根据类型和层级使用不同颜色
- **交互反馈**: 悬停、点击状态的视觉反馈

## 🚀 开发指南

### 环境要求
- Node.js >= 16.x
- npm >= 8.x 或 yarn >= 1.x

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

启动后访问 `http://localhost:5173`（Vite 默认端口）

### 构建生产版本

```bash
npm run build
```

构建产物输出到 `dist/` 目录

### 预览生产构建

```bash
npm run preview
```

## ⚙️ 配置说明

### Vite 配置 (`vite.config.js`)

```javascript
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')  // 路径别名
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',  // 后端API地址
        changeOrigin: true
      }
    }
  }
})
```

### 环境变量

项目支持使用 `.env` 文件配置环境变量：

- `VITE_API_BASE_URL`: API 基础地址（如需要）

## 🎯 核心特性

1. **多维度数据展示**
   - 来源列表（卡片式布局）
   - 时间线（垂直时间轴）
   - 因果关系（原因-结果链）
   - 知识图谱（网络图）
   - 层次结构（树状图）
   - 深度分析（文本摘要）

2. **交互式可视化**
   - 可拖拽、缩放、悬停查看详情
   - 图谱/列表视图切换
   - 节点点击事件处理

3. **响应式设计**
   - 适配不同屏幕尺寸
   - 侧边栏折叠/展开
   - 网格布局自适应

4. **用户体验优化**
   - 加载状态提示
   - 空状态展示
   - 错误信息友好提示
   - 置信度可视化

## 📝 代码特点

### Vue 3 Composition API 最佳实践

- 使用 `<script setup>` 语法糖，代码更简洁
- 使用 `ref` 和 `computed` 实现响应式
- 使用 `onMounted` 和 `watch` 处理生命周期和监听

### 性能优化

- 路由懒加载
- 图表库按需加载（CDN）
- 计算属性缓存
- 条件渲染优化

### 代码组织

- 功能模块化（API、工具、组件分离）
- 单一职责原则
- 可复用组件设计

