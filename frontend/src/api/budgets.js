import request from './request'

export function getBudgets(params) {
  return request.get('/budgets', { params })
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
