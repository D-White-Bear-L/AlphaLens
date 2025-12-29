import { createApp } from 'vue'
// import './style.css'
import App from './App.vue'
import 'element-plus/dist/index.css'
import router from './router/index.js'
import ElementPlus from 'element-plus'
// import permission from './directives/permission'

const app = createApp(App)
app.use(router)
app.use(ElementPlus)
// app.use(permission) // 权限指令
app.mount('#app')

