import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
// v1.4.3 M4：Vuetify 内置文案中文化（日历标题/星期/月份等）。
// vite-plugin-vuetify 未启用 → 走显式 import，零新增依赖（包内已有 vuetify）
import { zhHans } from 'vuetify/locale'
import '@mdi/font/css/materialdesignicons.css'
import './styles/global.scss'

const vuetify = createVuetify({
  components,
  directives,
  // v1.4.3 M4（需求四）：全站 Vuetify 内置文案中文——日历标题/星期/月份等
  locale: {
    locale: 'zhHans',
    messages: { zhHans },
  },
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#8B7E74',      // 灰褐色主色
          secondary: '#A8988E',    // 浅灰褐色
          accent: '#C4B5A8',       // 更浅的灰褐色
          error: '#E57373',
          warning: '#FFB74D',
          success: '#81C784',
          info: '#64B5F6',
          background: '#F5F0EB',   // 米白背景
          surface: '#FFFFFF',
          'surface-variant': '#F0EBE6',
          'on-surface': '#1C1B1F',
          'on-surface-variant': '#49454F',
        },
      },
      dark: {
        colors: {
          primary: '#A8988E',      // 深色模式下略亮
          secondary: '#8B7E74',
          accent: '#7A6E64',
          error: '#EF5350',
          warning: '#FFA726',
          success: '#66BB6A',
          info: '#42A5F5',
          background: '#1E1E1E',
          surface: '#2C2C2C',
          'surface-variant': '#2C2C2C',
          'on-surface': '#E6E1E5',
          'on-surface-variant': '#CAC4D0',
        },
      },
    },
  },
  defaults: {
    VBtn: {
      rounded: 'xl',
    },
    VCard: {
      rounded: 'xl',
    },
    VTextField: {
      variant: 'outlined',
      density: 'compact',
    },
    VSelect: {
      variant: 'outlined',
      density: 'compact',
    },
    // v1.4.3 M14（需求十四 任务 7.1）：菜单/下拉类展开画面统一「自触发点缩放浮现」过渡。
    // 实测 Vuetify 3.12 的 VSelect 把自己的 transition（默认 VDialogTransition 对象）直传 VMenu，
    // 故 defaults.VMenu 对 v-select 不生效 → 站内 v-select/v-autocomplete 调用点同步显式传
    // transition="fab-transition"（设计 §14.2.3 预留的兜底分支，站点使用量小可枚举）。
    VMenu: {
      transition: 'fab-transition',
    },
    VNavigationDrawer: {
      rounded: 'xl',
    },
  },
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(vuetify)
app.mount('#app')
