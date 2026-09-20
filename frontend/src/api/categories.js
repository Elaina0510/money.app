import request from './request'

export function getCategories(params = {}) {
  return request.get('/categories', { params })
}

export function createCategory(data) {
  return request.post('/categories', data)
}

export function updateCategory(id, data) {
  return request.put(`/categories/${id}`, data)
}

// 批量重排：body { ids }（v1.4.3 M8 起为全量单列表的有序 id），「其他」由服务端强制置尾
export function reorderCategories(data) {
  return request.put('/categories/reorder', data)
}

export function deleteCategory(id) {
  return request.delete(`/categories/${id}`)
}

export function restoreDefaultCategories() {
  return request.post('/categories/restore-defaults')
}
