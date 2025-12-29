import { createRouter, createWebHistory } from 'vue-router'
import LayOut from '@/layout.vue'

const routes = [
  // 主布局 - 首页
  {
    path: '/',
    component: LayOut,
    redirect: '/chat',
    meta: {
      requiresAuth: false
    },
    children: [
      { 
        path: 'chat', 
        name: 'Chat', 
        component: () => import('@/views/Chat/ChatView.vue'),
        meta: {
          title: 'AI Agent 助手',
          requiresAuth: false
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

