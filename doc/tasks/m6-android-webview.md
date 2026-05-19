# 模块六：安卓 WebView 封装模块 (M6) — 任务分解

> **对应需求**：安卓端 WebView 封装  
> **前置依赖**：M5 前端 UI 模块完成（依赖 `dist/` 构建产物）  
> **预估工时**：2-4小时

## 任务清单

### 1. 安卓项目初始化

- [ ] 使用 Android Studio 创建新项目（Empty Activity）于 `android/` 目录
- [ ] 配置 `build.gradle.kts`（项目级别和应用级别）
- [ ] 配置 `settings.gradle.kts`
- [ ] 配置 `gradle.properties`
- [ ] 配置 `app/proguard-rules.pro`

### 2. AndroidManifest 配置

- [ ] 添加权限声明：
  - [ ] `android.permission.CAMERA` — 相机权限
  - [ ] `android.permission.INTERNET` — 网络权限
  - [ ] `android.permission.READ_EXTERNAL_STORAGE` — 读取存储
  - [ ] `android.permission.WRITE_EXTERNAL_STORAGE`（maxSdkVersion=28）— 写入存储
- [ ] 配置 `AndroidManifest.xml`（允许 HTTP 明文访问用于开发调试）

### 3. WebView 核心实现

- [ ] 创建 `MainActivity.kt` — 应用主入口
- [ ] 创建 `WebViewActivity.kt` — WebView 配置：
  - [ ] 启用 JavaScript
  - [ ] 启用 DOM Storage
  - [ ] 配置 Viewport（`loadWithOverviewMode`, `useWideViewPort`）
  - [ ] 禁用缩放控制
  - [ ] 允许文件访问
  - [ ] 支持加载本地 `file:///android_asset/www/index.html`（发布模式）
  - [ ] 支持加载远程 URL（开发模式，如 `http://10.0.2.2:5173`）

### 4. JS 桥接接口 (WebAppInterface)

- [ ] 创建 `WebAppInterface.kt`，暴露以下方法给前端：
  - [ ] `takePhoto()` — 调用系统相机拍照，返回图片 Base64
  - [ ] `pickFromGallery()` — 从相册选择图片，返回图片 Base64
  - [ ] `showToast(msg: String)` — 显示原生 Toast
  - [ ] `getAppVersion(): String` — 获取 App 版本号
  - [ ] `vibrate(ms: Long)` — 触觉反馈震动
- [ ] 在 WebView 中注册 JS 接口：`webView.addJavascriptInterface(WebAppInterface(this), "Android")`

### 5. 相机拍照功能

- [ ] 创建 `CameraHelper.kt` — 相机拍照辅助类
- [ ] 实现拍照流程：
  - [ ] 启动相机 Intent
  - [ ] 拍照完成后获取图片数据
  - [ ] 将图片转换为 Base64 字符串
  - [ ] 通过 JS 回调返回给前端
- [ ] 实现相册选择流程：
  - [ ] 启动相册 Intent
  - [ ] 选择图片后转换为 Base64
  - [ ] 通过 JS 回调返回给前端

### 6. 前端构建产物集成

- [ ] 构建前端：`cd frontend && npm run build`
- [ ] 创建目录 `android/app/src/main/assets/www/`
- [ ] 将 `frontend/dist/` 所有文件复制到 `android/app/src/main/assets/www/`
- [ ] 配置 WebView 加载本地文件：`webView.loadUrl("file:///android_asset/www/index.html")`

### 7. UI 与主题

- [ ] 创建 `res/layout/activity_main.xml` — 根布局（容纳 WebView）
- [ ] 创建 `res/values/strings.xml` — 应用名称等字符串
- [ ] 创建 `res/values/themes.xml` — Material You 主题配置
- [ ] 创建应用图标（mipmap 各分辨率）

### 8. 构建与调试配置

- [ ] 支持 debug 模式（加载远程开发服务器地址）
- [ ] 支持 release 模式（加载本地 assets）
- [ ] 配置构建变体（Build Variants）

### 9. 验证与测试

- [ ] 使用 Android Emulator 运行应用
- [ ] 确认 WebView 正确加载前端页面
- [ ] 确认底部导航等交互正常工作
- [ ] 测试相机拍照功能（需真机或带相机模拟的模拟器）
- [ ] 测试从相册选取图片
- [ ] 测试 Toast 和震动反馈
- [ ] 生成 APK 并验证安装
