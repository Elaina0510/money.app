import request from './request'

export function getTags() {
  return request.get('/tags')
}

export function getTag(id) {
  return request.get(`/tags/${id}`)
}

export function createTag(data) {
  return request.post('/tags', data)
}

export function updateTag(id, data) {
  return request.put(`/tags/${id}`, data)
}

export function deleteTag(id) {
  return request.delete(`/tags/${id}`)
}
