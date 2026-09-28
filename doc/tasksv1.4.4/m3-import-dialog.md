# M3 - 导入映射弹窗：三段式钳高 + 新建分类自定义名（REQ-006 / REQ-007）

> 对应设计 §四（决策 D5 钳高在组件内部、D10 `name` 可选字段）。目标：`CsvMappingDialog.vue` 内部三段式（头固定/中段滚动/底固定，90vh 定值）；分类映射 `create` 载荷新增可选 `name`，前端「编辑过才发」保向后兼容。
> 涉及文件：改 `backend/app/schemas/import_.py`、`backend/app/services/import_service.py`（`_apply_category_action` 区域）、后端导入既有测试文件；改 `frontend/src/components/common/CsvMappingDialog.vue`，新增 `frontend/src/components/common/CsvMappingDialog.test.js`（**该组件现无测试文件，已核验**）。
> 依赖：**M2 必须先合入**（§2.3 同文件——`import_service.py` 三处 `source=0` 已在位，开工重读落盘后行号，勿回退）。与 M1/M4/M5 零文件交叉。
> 行号为设计快照参考位，开工以 grep 定位为准。

---

## 1. 后端：载荷契约（`schemas/import_.py`）

- [x] 1.1 `CategoryMappingItem` 新增 `name: str | None = None`（仅 `action="create"` 生效）；**既有废弃字段 `type` 原样保留不删**（红线）
- [x] 1.2 `ImportCsvRequest`/`ImportSqlRequest` 的 `category_mapping` 转 dict 链路（`model_dump`）零改动——SQL 请求同用该 item 模型自动获得能力，**无行为承诺变化**
  > 实测核验：`app/routers/import_.py` 的 `model_dump()` 链路（:51 / :116）未增删一行即自动带出 `name`；
  > 服务层按 `mapped.get("name")` 取用，键缺席 → `None` → 回退原分类名，故两型请求共用同一形状。

## 2. 后端：服务层（`import_service._apply_category_action`，约 :512-526）

- [x] 2.1 新增模块内私有 `_clean_create_name(raw)`：`None→""`、去首尾空白
- [x] 2.2 `create` 分支建类名 = `_clean_create_name(name) or 行内原分类名`；结果空 → 回退原分类名（**不报错、不跳过**——REQ-007「空按预填值」口径）
- [x] 2.3 回退后仍为空（原分类名本身空/含 `/`）→ 维持现状返回 `None` 走 V3 兜底链
- [x] 2.4 同名复用（`_resolve_or_create_category`）与批内 memo 去重语义不变——**memo 键沿用文件内原分类名（行匹配键），类目落名用自定义名**（映射「买菜」时同批多行原分类名相同仍复用同一新类）
- [x] 2.5 后端兜底：绕过前端直发重名 create → 同名复用既有行（不炸、不重复建类、**不新增 400**——与现状同名语义一致）
- [x] 2.6 改动范围锁死在 `_apply_category_action` 及辅助函数；识别区/容器分派/SQL 区零 hunk
  > 执行登记：本文件只有三处 hunk——新增 `_clean_create_name`、`_apply_category_action` 增
  > `create_name` 形参与 create 分支回退、`_resolve_row_category` 调用点补传 `mapped.get("name")`。
  > `fallback_category`（V3 链的第二档）**故意不带 name**——该路径载荷与 boot3 逐字同形，不新造语义。
  > memo 仍按 `cat_name`（文件内原分类名）键入，落名用自定义名 → §5.5 与「memo 键」断言两条都成立。
  > M2 遗留三处 `source=0` 注释仍在位、未回退；本模块 +35 行使后两处下移，实测当前行号
  > :390 / :1331 / :1677（M2 交付时为 :390 / :1296 / :1642）；`_resolve_or_create_category` 本体未改。

## 3. 前端：三段式钳高（REQ-006，D5；只改 `CsvMappingDialog.vue`）

- [x] 3.1 样式：`.mapping-card { display: flex; flex-direction: column; max-height: 90vh; }`、`.mapping-body { flex: 1 1 auto; min-height: 0; overflow-y: auto; }`
- [x] 3.2 模板三段：① 标题区（现 `v-card-title` + `格式：… 共 N 条记录` caption，移出原平铺层，固定不滚）② `div.mapping-body` 包住**现有全部映射内容**（区块一/二 + 分类映射 + 标签映射 + 未映射计数 + 缺项清单），唯一纵向滚动段，**挂 `tabindex="0"`**（键盘可聚焦滚动容器，ui-design 十四章，2026-09-28 审查补；除此之外不加样式类）③ 底部取消/确认两钮固定恒见（位置不变）
- [x] 3.3 口径：`AppDialog` 维持 `max-width="480"`、**不加 `scrollable`**（钳高在卡片自身，展开动画零影响）；内容短于 90vh 随内容收缩无留白；不动全站 AppDialog 壳（§0.6）；`v-card.mapping-card` 保留 `pa-4`，其上 `rounded="xl"` 系被 global.scss 压至弹层 20px 的遗留属性——不移除、不依赖其圆角值（ui-design 审查裁定）
- [x] 3.4 `sample-scroll` 横向滚动、`mb-4` 间距逻辑、SQL 复用路径的 v-if 隐藏语义**全部不动**；中段仅 `overflow-y`，不引横向滚动条
- [x] 3.5 边界自查：视口极矮（<480px 高）时标题+底部仍可见（中段 flex 收缩至 0 仍可滚）
  > 执行登记：设计 §4.1 两行声明逐字落地；`.mapping-body` **另加** `overflow-x: hidden`——
  > 单轴取 `auto` 时浏览器会把另一轴的 `visible` 计算成 `auto`，17 列样例行会把中段撑出
  > 一条横向滚动条，正是 §4.1 禁止的那条；横向滚动仍由 `.sample-scroll` 自己承担。
  > 中段容器的模板类清单实测为 `class="mapping-body" tabindex="0"`（无其他样式类，正则锁在 §6.1）。
  > 3.5 静态自查：标题/底部两个 `<div>` 未设 `min-height: 0` → 取内容最小高度不被压没，
  > 中段显式 `min-height: 0` → 可收缩至 0 仍保持 `overflow-y: auto` 可滚（jsdom 无布局引擎，
  > 真机观感属 §7.5 人工项）。

## 4. 前端：新建分类自定义名（REQ-007；同文件）

- [x] 4.1 选 `+ 新建分类` → 该行下方内联 `v-text-field`（density compact、outlined、**预填原分类名**；不做 `data-testid` 要求，测试以行结构断言）
- [x] 4.2 状态：`categoryMapping[catName] = { action: 'create', name?, _touched? }`；`_touched` 为本地标记**不发往后端**；**仅当用户编辑过输入框**（含清空重输）才在 `handleConfirm` 载荷带 `name`；未编辑 → 载荷 `{action:'create'}` 与旧版**逐字一致**
- [x] 4.3 实时校验（watch 本批全部 create 名）：
  - 去空白后为空 → 视为未改名（不报错、不发 name、按预填值）
  - 与本批其他新建名重复（两侧去空白、大小写精确比较）→ 行下 `text-caption text-error`：`与本次新建的其他分类重名`
  - 与 `props.categories` 现有可见分类名重复 → 行下报错：`分类「X」已存在，请换一个名称`
  - 报错计入禁用条件 →「确认导入」置灰；报错在弹窗内可见，**不依赖 toast**
- [x] 4.4 `unmappedCount` 对 create 行判定不因 `name` 变化（既有 `action==='create'` 即视为已映射）
  > 执行登记（两处口径偏离，均为「不动既有测试」红线所迫，功能语义不变）：
  > ① **4.1 的输入元素取原生 `<input class="create-name-input">`，非 `v-text-field`**——本批不触碰的
  > `SettingsSubPages.test.js` 用例 M4-9 以 `?raw` 把模板内 Vuetify 标签集合**封闭**为七件套
  > （`v-btn/v-card/v-card-title/v-icon/v-radio/v-radio-group/v-select`），引入 `v-text-field` 会把
  > 一条既有绿灯直接改红。compact / outlined 观感由 scoped 样式对齐同排 `v-select`（1px 描边、
  > 4px 圆角、14px 字号、placeholder 用原分类名），焦点环沿用 global.scss 的 `*:focus-visible`。
  > ② **4.3 用 `computed`（`createNameErrors`）而非 `watch`** 承载实时校验——响应式效果同价，
  > 少一个副作用源；报错**计入禁用条件**的方式是把条数折进既有的 `missingRequiredCount`
  > （= 必需列缺项 + 新建名重名条数），使模板里被逐字断言的
  > `:disabled="unmappedCount > 0 || missingRequiredCount > 0"` 表达式**一字不动**、不并列出第四个数；
  > 底部缺项清单仍**只**渲染列级缺项，新建名报错只在**该行下方**就地可见。
  > ③ 顺带一处必要修正：缺项清单容器的门槛由 `v-if="missingRequiredCount > 0"` 改为
  > `v-if="missingRequired.length > 0"`——折进新建名条数后，旧门槛会在「只有重名报错」时渲染出
  > 一个**空的原因清单**（底部空白、无字），改后底部只在真有列缺项时出现，重名报错一律行内可见。
  > 该字面量不在既有断言里，全量测试绿（vitest 458）佐证无回归。

## 5. 后端测试（追加至导入既有测试文件，设计 §4.3 五条）

- [x] 5.1 `{action:'create', name:'买菜'}` → 建类名逐字「买菜」、对应账单归入；`GET /categories` 可见
- [x] 5.2 `name:"  "`（全空白）→ 按原分类名建类（回退口径）
- [x] 5.3 **无 `name` 字段的旧载荷 → 行为与 boot3 终验逐字一致**（回归锚）
- [x] 5.4 `name` 与既有分类同名 → 复用既有类 id，不新建、不报错
- [x] 5.5 同批两行原分类名相同、自定义名「买菜」→ 仅建一个「买菜」（memo 键口径）
  > 执行登记：五条设计用例 + 1 条 memo 键直证用例，全部**追加**在既有
  > `backend/tests/test_csv_import_export.py` 末尾的新类 `TestCsvM3CreateName`（6 个 test，未新建文件、
  > 未改任何既有测试，SQL 侧导入测试同样零修改）。
  > §5.3 回归锚的做法：同一条账单分别用「不带 `name` 键」与「`name: None`」导入两次，逐字段比对
  > 落库分类名与账单归属完全相同，另加两条单元断言
  > `CategoryMappingItem(action="create").name is None`、`import_service._clean_create_name(None) == ""`。
  > §5.5b 直接调 `_resolve_row_category`，断言 `list(memo) == ["外卖"]`（键 = 文件内原分类名）
  > 且落库类目名 = 「买菜」、`categories` 表只多一行。

## 6. 前端测试（**新文件** `CsvMappingDialog.test.js`，设计 §4.3 五条）

- [x] 6.1 源码正则（`?raw` 断言范式）：`.mapping-card` 含 `max-height: 90vh` 与 flex column；`.mapping-body` 含 `overflow-y: auto` 与 `min-height: 0`；模板中底部操作区 div 在 `mapping-body` **之外**；`mapping-body` 容器带 `tabindex="0"`（键盘可达补口径）
- [x] 6.2 选 create → 输入框出现且预填值 == 原分类名；未编辑直接确认 → 载荷该 key **无 `name` 字段**
- [x] 6.3 输入「餐饮」（已存在）→ 行内 `text-error` 节点存在 + 确认按钮 disabled；改回合法名 → 报错消失、按钮恢复、载荷 `name` 为新值
- [x] 6.4 输入清空 → 报错不出现、载荷无 `name`（预填值生效口径）
- [x] 6.5 本批两行分别新建同名 → 后一行报错禁用
  > 执行登记：新文件 `frontend/src/components/common/CsvMappingDialog.test.js`，8 条用例覆盖 §6.1–§6.5：
  > §6.1 → M3-1/M3-2/M3-3（样式声明断言**先剥 CSS 注释**再取规则体，避免被说明文字误判通过；
  > 操作区是否在中段之外用 `mapping-body` 配对 `</div>` 的**逐层计数扫描**定区间后比索引），
  > §6.2 → M3-4（并断言本地态含 `name`/`_touched=false` 而出网载荷只有 `{action:'create'}`），
  > §6.3 → M3-5，§6.4 → M3-6（含全空白与真空串两种清空），§6.5 → M3-7，
  > 另加 M3-8（map 行载荷 / SQL 复用请求体键集两字段不变 / 首尾空白原样出网交后端清洗）。
  > 本文件是**新建独立**测试文件：boot3 的 CSV describe 仍留在 `SettingsSubPages.test.js`（未追加、未改），
  > 两条 mount 路径并存，`?raw` 断言范式与该文件同源。

## 7. 验收门槛

- [x] 7.1 本模块前后端测试全绿；全量 `pytest` / `npx vitest run` 绿（对向泳道在途红灯按 E3 归属登记）
  > 实测：`backend` 全量 `pytest tests/ -q` → **727 passed**（0 failed，无对向泳道红灯，E3 未触发）；
  > `frontend` 全量 `npm test` → **458 passed / 17 files**（0 failed）。本模块新增：后端 6 条 + 前端 8 条。
- [x] 7.2 mypy 基线零新增；ruff clean；eslint 基线零新增
  > 实测：`mypy app` → **83 errors**（开工基线 83，零新增）；`ruff check app tests` → **All checks passed**；
  > `npm run lint` → **0 errors / 2 warnings**，两条 warning 仍是既有的 `previewData` / `categories`
  > `vue/require-default-prop`（未新增 Props，基线原样）。
- [x] 7.3 红线自查：不重构 AppDialog 壳、不引 v-stepper/新依赖；`CsvMappingDialog.vue` **不重命名**；`CategoryMappingItem.type` 空转字段未删；SQL 导入弹窗复用路径零回归（既有 SQL 侧测试零修改）
  > 自查结果：`AppDialog.vue` / `global.scss` 未出现在改动集（壳零改动）；无新依赖（`package.json` /
  > `requirements` 未动）；组件文件名与既有函数名保持；`type` 字段仍在 schema；
  > `SettingsSubPages.test.js`（含 boot3 CSV describe 与 SQL 复用用例）**一字未改**，
  > 模板内 Vuetify 标签集合、两处 `previewData?.columns` v-if、`:disabled` 字面量均通过其既有断言。
- [x] 7.4 pathspec 精确提交：§「涉及文件」全清单 + 本任务文件；不 push
  > 本次提交 pathspec（逐条点名，不使用 `-A`/`.`/`-f`，不含 dist / progress.md）：
  > `backend/app/schemas/import_.py`、`backend/app/services/import_service.py`、
  > `backend/tests/test_csv_import_export.py`、`frontend/src/components/common/CsvMappingDialog.vue`、
  > `frontend/src/components/common/CsvMappingDialog.test.js`、`doc/tasksv1.4.4/m3-import-dialog.md`。
  > 工作区里 `.claude/skills/ui-design.md` 等他人在途改动**不并入**本提交。
- [ ] 7.5 真机项**不勾选**、原文抄入 progress.md 人工清单：1280×720 导入 17 列 Cashew 全量——确认按钮不出屏、映射行全部可滚动触达；短文件无多余留白；SQL 弹窗复用不回归

**验收标准（REQ-006/007）**：弹窗整体 ≤90vh、超限时仅中段滚动、标题与按钮恒可见；「买菜」改名导入后分类名逐字一致；不改名行为与旧版一致；重名时确认禁用且报错在弹窗内可见。
