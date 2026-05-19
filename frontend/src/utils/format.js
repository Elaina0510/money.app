import dayjs from 'dayjs'

/**
 * Format amount with ¥ symbol
 */
export function formatAmount(amount) {
  if (amount === null || amount === undefined) return '¥0.00'
  return `¥${Number(amount).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

/**
 * Format date string
 */
export function formatDate(dateStr, format = 'MM月DD日') {
  if (!dateStr) return ''
  return dayjs(dateStr).format(format)
}

/**
 * Format datetime string
 */
export function formatDateTime(dateStr) {
  if (!dateStr) return ''
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm')
}

/**
 * Format file size
 */
export function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(1)} ${units[i]}`
}

/**
 * Get record type color
 */
export function getTypeColor(type) {
  return type === 'expense' ? '#FF6B6B' : '#20C997'
}

/**
 * Get type label
 */
export function getTypeLabel(type) {
  return type === 'expense' ? '支出' : '收入'
}

/**
 * Get current month range
 */
export function getCurrentMonthRange() {
  const now = dayjs()
  return {
    startDate: now.startOf('month').format('YYYY-MM-DD'),
    endDate: now.endOf('month').format('YYYY-MM-DD'),
  }
}

/**
 * Get month range for specific period
 */
export function getMonthRange(offset = 0) {
  const target = dayjs().add(offset, 'month')
  return {
    startDate: target.startOf('month').format('YYYY-MM-DD'),
    endDate: target.endOf('month').format('YYYY-MM-DD'),
    label: target.format('YYYY年MM月'),
  }
}

/**
 * Get year range
 */
export function getYearRange(year) {
  const target = dayjs().year(year || dayjs().year())
  return {
    startDate: target.startOf('year').format('YYYY-MM-DD'),
    endDate: target.endOf('year').format('YYYY-MM-DD'),
    label: target.format('YYYY年'),
  }
}
