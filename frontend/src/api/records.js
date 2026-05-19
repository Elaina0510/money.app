import request from './request'

export function getRecords(params = {}) {
  return request.get('/records', { params })
}

export function getRecord(id) {
  return request.get(`/records/${id}`)
}

export function createRecord(data) {
  return request.post('/records', data)
}

export function updateRecord(id, data) {
  return request.put(`/records/${id}`, data)
}

export function deleteRecord(id) {
  return request.delete(`/records/${id}`)
}

export function batchDeleteRecords(ids) {
  return request.post('/records/batch-delete', { ids })
}

export function getQuickTemplates() {
  return request.get('/records/quick-templates')
}
