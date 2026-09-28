import request from './request'

export function getTags() {
  return request.get('/tags')
}

// 分页取标签：返回 { items, total, page, page_size }（total 为匹配总数，含 q 过滤）
export function getTagsPaged(params) {
  return request.get('/tags/paged', { params })
}

export function searchTags(q) {
  return request.get('/tags', { params: { q } })
}

export function createTag(data) {
  return request.post('/tags', data)
}

export function deleteTag(id) {
  return request.delete(`/tags/${id}`)
}

// v1.4.4 M1（REQ-002）：批量软删当前用户的标签，后端单事务原子——任一 id 不属于本人/已软删
// 即整单 400（中文 message），零行落删除；载荷 ids 为去重后的选中集
export function batchDeleteTags(ids) {
  return request.post('/tags/batch-delete', { ids })
}

// v1.4.4 M1（REQ-001）：一键清空当前用户全部标签（无 body）；0 条也成功返回 deleted_count:0（幂等）
export function clearAllTags() {
  return request.post('/tags/clear-all')
}
