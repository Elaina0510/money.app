import request from './request'

export function getSummary(params = {}) {
  return request.get('/statistics/summary', { params })
}

export function getByCategory(params = {}) {
  return request.get('/statistics/by-category', { params })
}

export function getByTag(params = {}) {
  return request.get('/statistics/by-tag', { params })
}

export function getTrend(params = {}) {
  return request.get('/statistics/trend', { params })
}
