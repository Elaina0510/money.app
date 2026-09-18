# M3 - 账单页年份切换（含最早年份接口）

> 对应需求二：竖屏账单页支持切换年份；年份范围统一为"往前到最早记录年、往后不超当前年"。
> 决策 D1：新增轻量后端接口 `GET /api/records/earliest-year`，不改 `GET /api/records` 响应结构。
> 涉及文件：`backend/app/services/record_service.py`、`backend/app/routers/records.py`、`backend/tests/test_records.py`、`frontend/src/api/records.js`、`frontend/src/pages/RecordListPage.vue`
> 依赖：无。RecordListPage 与 M4/M5 同文件，按 M3 → M4 → M5 串行。

---

## 1. 后端：earliest-year 接口

### 1.1 Service（record_service.py）

- [x] 新增 `async def get_earliest_year(db: AsyncSession, current_user: User) -> int | None`
- [x] 查询：`select(func.min(func.substr(Record.consume_time, 1, 4))).where(Record.user_id == current_user.id)`
  （`consume_time` 为 `"%Y-%m-%d %H:%M:%S"` 字符串，substr(1,4) 即年份，字符串 MIN 等价年份 MIN）
- [x] 无记录返回 `None`，有记录返回 `int(year_str)`
- [x] 中文 docstring + 类型注解，全 async

### 1.2 Router（records.py）

- [x] 新增 `@router.get("/earliest-year")`，依赖 `get_session` + `require_auth`
- [x] 返回 `success_response(data={"earliest_year": year})`
- [x] **路由顺序强约束（易错点 1）**：声明在 `@router.get("/{record_id}")`（现 :110）之前（与 `/quick-templates` :74 同区），否则被路径参数抢占返回 422

### 1.3 后端测试（pytest）

- [x] 用例 1：登录用户有 2023/2025 两年记录 → 返回 2023
- [x] 用例 2：无记录用户 → `earliest_year: null`
- [x] 用例 3：数据隔离——用户 A 的最早年份不受用户 B 记录影响
- [x] 用例 4：未认证 → 401
- [x] 用例 5：路径不被 `{record_id}` 抢占（返回 200 而非 422，回归路由声明顺序）

## 2. 前端：API 层

- [x] `frontend/src/api/records.js` 新增 `getEarliestYear()`：`request.get('/records/earliest-year')`

## 3. 前端：RecordListPage.vue 月份切换条改造

### 3.1 状态与加载

- [x] 新增 `const minYear = ref(null)`（null = 未加载；加载后为最早记录年份）
- [x] 新增 `async function loadEarliestYear()`：
  - [x] `minYear.value = result?.earliest_year ?? currentYear`（无记录用户仅可看当前年）
  - [x] `catch` 兜底：`minYear.value = currentYear`（接口异常退化为仅当前年，不阻塞账单浏览）
- [x] `onMounted` 中追加 `loadEarliestYear()`（与现有加载并行发起）

### 3.2 箭头按钮模板（现 :53-62、:83-92）

- [x] 左箭头：去掉 `d-none d-md-flex`（竖屏显示，与宽屏样式一致）
- [x] 左箭头显示条件：`v-if="selectedYear > minYear"`（禁用条件从 currentYear-5 改为 minYear）
- [x] 右箭头：去掉 `d-none d-md-flex`；显示条件维持 `v-if="selectedYear < currentYear"`

### 3.3 翻页函数

- [x] `prevYear()`：开头加双保险守卫 `if (minYear.value !== null && selectedYear.value - 1 < minYear.value) return`，再执行 `selectedYear.value--`、`selectedMonth.value = null`
- [x] `nextYear()`：维持现有 `selectedYear < currentYear` 守卫（:244-249）不动
- [x] 切换年份后仍渲染该年 1–12 月芯片（`v-for="m in 12"` :64 不变），点击 `selectMonth(m)` 行为不变

## 4. 前端测试（vitest，RecordListPage.test.js 扩展）

- [x] 竖屏（mock window.innerWidth < 960）渲染左右箭头
- [x] `selectedYear === minYear` 时左箭头不存在；`selectedYear === currentYear` 时右箭头不存在
- [x] `earliest_year=null` → 左箭头不存在（minYear 落到当前年）

## 5. 手工验收

- [ ] 竖屏可逐年翻到最早有记录的年份，查看该年 1–12 月账单
- [ ] 到达最早记录年：左箭头隐藏；到达当前年：右箭头隐藏
- [ ] 无账单新用户：仅当前年，左箭头不显示
- [ ] 宽屏行为同步符合新范围规则
- [ ] 接口失败场景（可 mock）：账单页核心功能不受阻塞

## 6. 质量门槛

- [x] `cd backend && python -m pytest tests/test_records.py -v` 通过
- [ ] `cd backend && python -m mypy app/ --ignore-missing-imports` 通过（v1.4 基线即存在 100+ 处项目级历史报错，非本模块引入；本模块新增代码零报错）
- [x] `cd backend && python -m ruff check app/ tests/` 通过
- [x] `cd frontend && npm test && npm run lint && npm run build` 通过
