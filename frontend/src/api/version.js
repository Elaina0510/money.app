import request from './request'

// v1.4.4 M4（REQ-008）：版本号唯一下取入口。后端真值定义于 backend/app/constants.py，
// 经无鉴权 GET /api/version 下发——前端不镜像、不硬编码任何版本字面量（改常量即全站生效）。
// request 拦截器已解 {code, message, data} 外壳，此处再解包 data.version 供页面直接消费。
export async function getAppVersion() {
  const data = await request.get('/version')
  return data.version
}
