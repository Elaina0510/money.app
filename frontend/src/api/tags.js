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
