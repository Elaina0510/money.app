import request from './request'

export function getRecords(params = {}) {
  return request.get('/records', { params })
}

export function getEarliestYear() {
  return request.get('/records/earliest-year')
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

export function addQuickTemplate(data) {
  return request.post('/records/quick-templates', data)
}

export function deleteQuickTemplate(id) {
  return request.delete(`/records/quick-templates/${id}`)
}

// 自动模板无 id：按签名 (tag_id, type, amount_cents) 永久忽略（金额单位：分，M6/D9 同口径）
export function ignoreAutoQuickTemplate(params) {
  return request.delete('/records/quick-templates/auto', { params })
}
