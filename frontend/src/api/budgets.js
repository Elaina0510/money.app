import request from './request'

// v1.4.3 M12：预算模型改为「某自然月下的多条具名预算」。
// 契约（决策 D12）：GET 去 type 参数；POST 为纯创建（同月同名允许多条）；
// PUT 为全字段编辑且 month 不可改；原「整月批量覆盖」端点已下线，其封装随之删除。

export function getBudgets(params) {
  return request.get('/budgets', { params })
}

// 年视图逐月预算汇总（v1.4.1 M6：统计页预算区块）
// months[].total_amount / total_spent = Σ 该月各预算（决策 D4，范围重叠时属预期）
export function getBudgetYearSummary(params) {
  return request.get('/budgets/year-summary', { params })
}

// 纯创建：载荷 {month, name, amount, scope_mode, category_ids}
export function createBudget(data) {
  return request.post('/budgets', data)
}

// 全字段编辑：载荷 {name, amount, scope_mode, category_ids}（month 不可改，不随载荷提交）
export function updateBudget(id, data) {
  return request.put(`/budgets/${id}`, data)
}

export function deleteBudget(id) {
  return request.delete(`/budgets/${id}`)
}
