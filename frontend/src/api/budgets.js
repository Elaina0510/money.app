import request from './request'

export function getBudgets(params) {
  return request.get('/budgets', { params })
}

// 年视图逐月预算汇总（v1.4.1 M6：统计页预算区块）
export function getBudgetYearSummary(params) {
  return request.get('/budgets/year-summary', { params })
}

export function batchSetBudgets(data) {
  return request.post('/budgets/batch', data)
}

export function updateBudget(id, data) {
  return request.put(`/budgets/${id}`, data)
}

export function deleteBudget(id) {
  return request.delete(`/budgets/${id}`)
}
