import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/pages/DashboardPage.vue'),
    meta: { title: '首页', icon: 'mdi-view-dashboard-outline', nav: true },
  },
  {
    path: '/records',
    name: 'Records',
    component: () => import('@/pages/RecordListPage.vue'),
    meta: { title: '账单', icon: 'mdi-format-list-bulleted', nav: true },
  },
  {
    path: '/statistics',
    name: 'Statistics',
    component: () => import('@/pages/StatisticsPage.vue'),
    meta: { title: '统计', icon: 'mdi-chart-box-outline', nav: true },
  },
  {
    path: '/budget',
    name: 'Budget',
    component: () => import('@/pages/BudgetPage.vue'),
    meta: { title: '预算', icon: 'mdi-piggy-bank-outline', nav: true },
  },
  {
    path: '/add',
    name: 'AddRecord',
    component: () => import('@/pages/RecordFormPage.vue'),
    meta: { title: '记一笔', icon: 'mdi-plus-circle' },
  },
  {
    path: '/edit/:id',
    name: 'EditRecord',
    component: () => import('@/pages/RecordFormPage.vue'),
    meta: { title: '编辑账单', icon: 'mdi-pencil' },
  },
  {
    path: '/detail/:id',
    name: 'RecordDetail',
    component: () => import('@/pages/RecordDetailPage.vue'),
    meta: { title: '账单详情', icon: 'mdi-information-outline' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/pages/SettingsPage.vue'),
    meta: { title: '设置', icon: 'mdi-cog-outline' },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
