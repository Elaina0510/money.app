import request from './request'

/**
 * Export records as CSV.
 * Returns a Blob for download.
 */
export async function exportCsv() {
  const response = await request.get('/export/csv', {
    responseType: 'blob',
  })
  return response
}

/**
 * Export data as SQL backup.
 * Returns a Blob for download.
 */
export async function exportSql() {
  const response = await request.get('/export/sql', {
    responseType: 'blob',
  })
  return response
}

/**
 * Preview CSV import.
 * @param {File} file - The CSV file to preview
 */
export async function previewCsvImport(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/import/csv/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/**
 * Confirm CSV import with mapping.
 * @param {Object} data - { cache_id, format, category_mapping, tag_mapping }
 */
export async function importCsv(data) {
  return request.post('/import/csv', data)
}

/**
 * Preview SQL import.
 * @param {File} file - The SQL/SQLite file to preview
 */
export async function previewSqlImport(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/import/sql/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/**
 * Confirm SQL import.
 * @param {Object} data - { cache_id, format, is_third_party, merge_mode }
 */
export async function importSql(data) {
  return request.post('/import/sql', data)
}
