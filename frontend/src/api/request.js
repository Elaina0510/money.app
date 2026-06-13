import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor — 自动附加 JWT token
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
request.interceptors.response.use(
  (response) => {
    const res = response.data
    // If the response has our wrapper format
    if (res.code !== undefined) {
      if (res.code === 0) {
        return res.data
      }
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    return res
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      let msg = '请求失败'
      if (status === 401) {
        // Prefer backend message (e.g. "用户名或密码错误" from login endpoint)
        if (data && data.message) {
          msg = data.message
        } else {
          msg = '登录已过期，请重新登录'
          // Clear expired token
          localStorage.removeItem('token')
          localStorage.removeItem('username')
          localStorage.removeItem('userId')
          window.dispatchEvent(new CustomEvent('auth:logout'))
        }
      } else if (status === 400 || status === 422 || status === 500) {
        msg = (data && data.message) || '请求失败'
      }
      return Promise.reject(new Error(msg))
    }
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('请求超时'))
    }
    return Promise.reject(new Error('网络异常'))
  }
)

export default request
