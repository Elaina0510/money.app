import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

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
      const { status } = error.response
      let msg = '请求失败'
      if (status === 422) {
        msg = '参数错误'
      } else if (status === 500) {
        msg = '服务器错误'
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
