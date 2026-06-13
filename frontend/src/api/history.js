import request from './request'

/**
 * Get paginated history list.
 * @param {Object} params - { page, page_size }
 */
export async function getHistoryList(params) {
  return request.get('/history', { params })
}

/**
 * Get history detail with parsed snapshots.
 * @param {number} id - History entry ID
 */
export async function getHistoryDetail(id) {
  return request.get(`/history/${id}`)
}

/**
 * Execute rollback for a history entry.
 * @param {number} id - History entry ID
 */
export async function rollbackHistory(id) {
  return request.post(`/history/${id}/rollback`)
}
