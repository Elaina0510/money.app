// Category icon mapping
export const CATEGORY_ICONS = {
  // Expense
  '餐饮': 'mdi-food',
  '交通': 'mdi-bus',
  '购物': 'mdi-cart',
  '娱乐': 'mdi-gamepad',
  '医疗': 'mdi-hospital-box',
  '居住': 'mdi-home',
  '通讯': 'mdi-cellphone',
  '教育': 'mdi-school',
  '其他支出': 'mdi-cash-minus',
  // Income
  '工资': 'mdi-wallet',
  '兼职': 'mdi-briefcase',
  '红包': 'mdi-gift',
  '理财': 'mdi-finance',
  '其他收入': 'mdi-cash-plus',
}

// Category colors
export const CATEGORY_COLORS = {
  expense: ['#FF6B6B', '#FFA94D', '#FFD43B', '#69DB7C', '#38D9A9', '#4DABF7', '#748FFC', '#9775FA', '#F783AC'],
  income: ['#20C997', '#51CF66', '#94D82D', '#FCC419', '#FF922B', '#F06595', '#CC5DE8', '#845EF7'],
}

// Error code mapping
export const ERROR_MESSAGES = {
  40001: '参数错误',
  40002: '资源不存在',
  40003: '资源冲突',
  40004: '文件格式不支持',
  40005: '文件大小超过限制',
}

// Record types
export const RECORD_TYPES = {
  income: '收入',
  expense: '支出',
}

// Period options
export const PERIOD_OPTIONS = [
  { value: 'monthly', title: '月度' },
  { value: 'yearly', title: '年度' },
]
