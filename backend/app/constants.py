"""Application-wide constants (v1.4.4 M4 / 设计 D4).

`APP_VERSION` 是**全仓唯一的版本号定义点**：后端 `FastAPI(version=APP_VERSION)`、
`GET /api/version` 与前端「关于」页（`frontend/src/api/version.js` → `SettingsAboutPage.vue`）
全部读这一处，前端不镜像、不硬编码任何版本字面量（REQ-008 验收「改常量即全站生效」）。

口径（设计 §5.1 / 任务 §1.1）：
  * 文档版本随批次 bump，本文件是唯一落点；
  * `frontend/package.json` 的 `0.0.0` 为脚手架字段，**不动**（全局红线 §0.6）；
  * 新增/改动版本号前先全仓 grep 旧版本号字面量复核收敛面（任务 §5.3 自证）。
"""

APP_VERSION: str = "1.4.4"
