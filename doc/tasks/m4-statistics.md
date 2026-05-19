# 模块四：统计模块 (M4) — 任务分解

> **对应需求**：2.3 统计功能  
> **前置依赖**：M1 记账管理模块完成（依赖记账数据）  
> **预估工时**：2-3小时

## 任务清单

### 1. Pydantic Schema

- [ ] 创建 `app/schemas/statistics.py`：
  - `SummaryResponse`（total_income, total_expense, balance, transaction_count, period, start_date, end_date）
  - `CategoryStatItem`（category_id, category_name, icon, total, percentage, count）
  - `CategoryStatResponse`（items, total_expense）
  - `TagStatItem`（tag_name, total, count）
  - `TagStatResponse`（items）
  - `TrendItem`（period, income, expense, balance）
  - `TrendResponse`（items）

### 2. 业务逻辑层 (Service)

- [ ] 创建 `app/services/statistics_service.py`，实现以下方法：

  - [ ] `get_summary(db, period, start_date, end_date)` — 收支概览
    - 按日/周/月/年统计总收入、总支出、结余
    - 返回交易笔数
    - 使用 SQL 聚合查询（`SUM`, `COUNT`, `GROUP BY`）

  - [ ] `get_category_stats(db, type, start_date, end_date)` — 分类统计
    - 按分类统计支出金额和笔数
    - 计算各分类占比百分比（保留一位小数）
    - 按金额降序排列
    - 关联 `categories` 表获取分类名称和图标

  - [ ] `get_tag_stats(db, start_date, end_date)` — 标签统计
    - 通过 `record_tags` 关联表按标签文本分组统计
    - 返回各标签的总金额和出现次数
    - 按总金额降序排列

  - [ ] `get_trend(db, group_by, start_date, end_date)` — 收支趋势
    - 按月（`group_by=month`）或按年（`group_by=year`）分组
    - 每组的收入、支出、结余
    - 按时间顺序排列

### 3. 路由层 (Router)

- [ ] 创建 `app/routers/statistics.py`，注册路由：
  - [ ] `GET /api/statistics/summary` — 收支概览（参数：period, start_date, end_date）
  - [ ] `GET /api/statistics/by-category` — 分类统计（参数：type, start_date, end_date）
  - [ ] `GET /api/statistics/by-tag` — 标签统计（参数：start_date, end_date）
  - [ ] `GET /api/statistics/trend` — 收支趋势（参数：group_by, start_date, end_date）

### 4. 参数验证

- [ ] `period` 仅接受 `day / week / month / year`
- [ ] `group_by` 仅接受 `month / year`
- [ ] `type` 在分类统计中固定为 `expense`
- [ ] `start_date` 和 `end_date` 格式验证（YYYY-MM-DD）
- [ ] 日期范围超过合理范围（如未来日期）的处理

### 5. 边界与空数据处理

- [ ] 无数据的时间区间返回 0 而非报错（total_income=0, total_expense=0, balance=0）
- [ ] 分类统计为空时返回空列表
- [ ] 趋势数据中缺失月份的处理（返回 0 填充）

### 6. 验证与测试

- [ ] 通过 Swagger 测试各统计接口
- [ ] 先通过 M1 接口创建多笔不同分类的记账数据
- [ ] 验证收支概览的聚合计算正确性
- [ ] 验证分类统计的百分比总和是否为 100%
- [ ] 验证趋势数据的时间排序正确性
- [ ] 测试空数据区间的接口返回
