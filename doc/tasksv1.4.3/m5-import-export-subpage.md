# M5 - 导入导出改为设置二级页面（需求五）

> 对应需求五（设计 §五）。导入导出从设置页内联卡片迁出为独立二级页面（组件复用、业务不重写），设置页保留入口行卡。
> 涉及文件：新增 `frontend/src/pages/SettingsImportExportPage.vue`；修改 `frontend/src/router/index.js`、`SettingsPage.vue`、`SettingsSubPages.test.js`。
> 依赖：无。与 M7/M8 同触 `SettingsPage.vue` 但区域无交叉（M5 删 :93-145 导入导出段；M7 账号区；M8 分类摘要 :50-52、:287-288），可并行；合并时 template 大段以 M5 为主。新页外层 `.page-card` 自动继承 M6 疏朗化口径。

---

## 1. 路由

- [x] 1.1 `router/index.js` 追加（quick-templates 之后）：`{ path: '/settings/import-export', name: 'SettingsImportExport', component: () => import('@/pages/SettingsImportExportPage.vue'), meta: { title: '导入导出' } }`

## 2. 新页 `SettingsImportExportPage.vue`

- [x] 2.1 页头与其他二级页同款：返回箭头 + `text-caption text-grey`「导出账单或从备份恢复」（参考 `HistoryPage.vue:3-17` 结构）
- [x] 2.2 主体 `<div class="page-card">` 容器包裹迁入的 4 个 `v-list-item` 行与 `v-divider` 分组（CSV/SQL 两组现有排布原样迁移）
- [x] 2.3 **原样平移**模板块：隐藏 file inputs（原 `SettingsPage.vue:166-179`）、`CsvMappingDialog` 引用、SQL 确认 `v-dialog`、`showSqlMapping` 映射对话框（:181-223）
- [x] 2.4 **原样平移** script：`exporting/importing/csvPreviewData/sqlPreviewData/sqlCacheId/sqlFormat` 等状态 + `handleExportCsv/handleExportSql/triggerCsvImport/handleCsvFileSelect/handleCsvImport/triggerSqlImport/handleSqlFileSelect/handleSqlNext/handleSqlImport/downloadBlob` 全部函数（:349-478）——从 SettingsPage **剪切而非复制**（防双份）
- [x] 2.5 toast 继续走 `appStore.showToast`；API 继续走 `@/api/export`

## 3. SettingsPage 瘦身

- [x] 3.1 删除导入导出内联卡模板块（:93-145）+ 上述 script 段 + `CsvMappingDialog`/`@/api/export`/`dayjs` import（dayjs 若他处无引用则删）
- [x] 3.2 新增入口行卡（与「数据回溯」卡 :147-163 同构）：`v-card.mb-3.settings-card > v-list-item[to="/settings/import-export"]`，prepend `.entry-avatar` 36 + primary icon 20 `mdi-swap-vertical`，标题「导入导出」+ 副标题「导出 CSV/SQL，导入备份文件」，append `mdi-chevron-right`
- [x] 3.3 **红线**：`SettingsPage.vue` grep `csvMapping|sqlPreview|exportCsv` 必须零命中（测试锁死，防双份状态残留）

## 4. 边界自检（设计 §5.3）

- [x] 4.1 导入中途返回设置页：页面卸载，进行中请求回调不再触达组件；file input reset 逻辑未动
- [x] 4.2 直达 URL `#/settings/import-export`：走全局路由守卫（token 校验），与其他二级页一致

## 5. 测试（设计 §5.4，`SettingsSubPages.test.js`）

- [x] 5.1 新用例组「导入导出二级页」：挂载 `SettingsImportExportPage`，stub `api/export`——点「导出 CSV」调 `exportCsv` 且触发 blob 下载（stub `URL.createObjectURL`/anchor click）；「导入 CSV」点击触发隐藏 input click；`CsvMappingDialog` 渲染并 confirm 走 `importCsv`
- [x] 5.2 `SettingsPage.vue ?raw` 断言：无 `CsvMappingDialog`、无 `input type="file"`、含 `to="/settings/import-export"` 入口
- [x] 5.3 路由表用例（:710 风格）补 `['/settings/import-export', 'SettingsImportExport', '导入导出']`；:230 设置页 `to` 列表断言更新为含 import-export 的 4 项

## 6. 验收与质量门槛

- [x] 6.1 `npm test` 全绿；`npm run lint` 通过
- [ ] 6.2 手工自查：设置页点「导入导出」进二级页、返回正常；导出 CSV/SQL 文件真实下载；导入走映射/确认流程成功；设置主页不再出现内联四行；明暗主题、竖/宽屏
