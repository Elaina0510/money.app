import request from './request'

export function uploadAttachment(file, recordId = null) {
  const formData = new FormData()
  formData.append('file', file)
  if (recordId) {
    formData.append('record_id', recordId)
  }
  return request.post('/attachments/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}

export function getAttachment(id) {
  return request.get(`/attachments/${id}`)
}

export function deleteAttachment(id) {
  return request.delete(`/attachments/${id}`)
}

export function getRecordAttachments(recordId) {
  return request.get(`/records/${recordId}/attachments`)
}
