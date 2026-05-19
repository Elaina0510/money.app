import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'
import './styles/global.scss'

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#6750A4',
          secondary: '#625B71',
          accent: '#E8DEF8',
          error: '#F2B8B5',
          warning: '#FFD43B',
          success: '#81C995',
          info: '#4DABF7',
          background: '#FEF7FF',
          surface: '#FFFFFF',
          'surface-variant': '#F7F2FA',
          'on-surface': '#1C1B1F',
          'on-surface-variant': '#49454F',
        },
      },
      dark: {
        colors: {
          primary: '#D0BCFF',
          secondary: '#CCC2DC',
          accent: '#4A4458',
          error: '#F2B8B5',
          warning: '#FDD663',
          success: '#81C995',
          info: '#4DABF7',
          background: '#1C1B1F',
          surface: '#2B2930',
          'surface-variant': '#2B2930',
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
