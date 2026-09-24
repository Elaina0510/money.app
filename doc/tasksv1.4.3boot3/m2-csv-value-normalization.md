# M2 - 后端清洗层：金额 / 日期 / 收支三态纯函数（需求 C）

> 对应设计 §二。目标：把外部账单里的 `¥1,234.50`、`(12.00)`、`2026/9/24`、`2026年9月24日 8:30`、`2026-09-24 11:07:54.617083`、`不计收支` 这些形态，收敛成库内唯一安全表示（`abs` 后的两位小数金额 + `YYYY-MM-DD HH:MM` 文本时间 + `income|expense`）。
> 涉及文件：新增 `backend/app/services/csv_values.py`、新增 `backend/tests/test_csv_values.py`。**零接线**——`import_service.py` 的调用点属 M3（避免与本模块抢文件）。
> 依赖：无。与 M1 零文件交叉，**可并行**。

---

## 1. 新文件 `backend/app/services/csv_values.py`：三个纯函数

- [x] 1.1 `parse_amount(raw: str | None) -> float | None`（设计 D13）
  - 处理序：`None`/空 → `None`；`unicodedata.normalize("NFKC")`（全角数字/句点转半角）→ 剥 `¥ ￥ $ 元` 与全部空白与千分位逗号 → 剥**结尾** `元` → 括号形态 `(12.00)` 判为负 → `float()`；任何失败 → `None`（**不抛异常**）
  - 返回**保留符号**的值（绝对化在 M3 入库时做，D13），`0.0` 是合法值不得与失败混淆
  - `/`、`-`、`--`、`""`、纯空白 → `None`
- [x] 1.2 `parse_time(raw: str | None) -> str | None`（设计 D14）
  - 粗判前置：正则 `^\s*(19|20)\d{2}\s*[-/年]`，不通过直接 `None`（挡住 `09/24/2026`、`24/09/2026`、纯数字时间戳，D15）
  - `~` 时间区间 → 取 `~` 前段再解析
  - 按 §2 白名单**顺序**逐个 `datetime.strptime`，命中后 `strftime("%Y-%m-%d %H:%M")` 输出；**无时间成分的形态补 `00:00`**
  - **禁止按 `.` 截断**（现有 `convert_cashew_date` 的 `value[:16]` 即被本函数替换；微秒位数不固定，模板 6 位、全量导出 3 位）
  - 全部失败 → `None`
  - **xlsx 通道不改本函数**（D24）：M6 容器层已把日期单元格换算成 `"%Y-%m-%d %H:%M:%S"` 文本再进来（实测 `46289.48678240741` → `2026-09-24 11:40:58`），白名单成员与顺序**一字不改**；若用户在 Excel 里把该列改成「常规」再另存 CSV，进来的是裸序列号 → 粗判正则本就判 `None` 跳过，**不做序列号兜底**（D15 不猜）
- [x] 1.3 `resolve_type(raw: str | None, amount: float | None, source: str) -> tuple[str | None, str | None]`（设计 D10/D11）
  - 返回 `(type, skip_reason)`；`type ∈ {"income","expense",None}`，`skip_reason ∈ {None,"type_ignored","type_unresolved","invalid_amount"}`
  - `source == "column"`：按 §3 三集合判；`raw` 空或不可判 → `(None, "type_unresolved")`，**不得回落到 sign**（D10）
  - `source == "sign"`：`amount is None` → `(None, "invalid_amount")`；`amount < 0` → `expense`；`amount >= 0` → `income`（**0 归支出**）
  - `source == "all_expense"` / `"all_income"`：常量返回
  - 其它 `source` 值 → `(None, "type_unresolved")`（不猜）
- [x] 1.4 类型注解完整；模块**不 import** `csv_dialects`、**不 import** ORM/config（零耦合，M3 单向依赖）

## 2. `TIME_FORMATS` 白名单（逐字抄录，顺序即匹配优先级，禁止增删）

```python
TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d",
    "%Y年%m月%d日 %H:%M:%S", "%Y年%m月%d日 %H:%M", "%Y年%m月%d日",
)
```

- [x] 2.1 白名单作为模块级常量导出，供 §4.3 一致性断言逐位钉死
- [x] 2.2 输出恒为 16 字符、补零、24 小时制（`strptime` 容忍 `8:30`/`9/24` 非补零输入，输出侧由 `strftime` 统一补零）

## 3. 收支值三集合（设计 D11，逐值抄录）

```python
TYPE_VALUE_EXPENSE = {"支出", "支", "expense", "out", "debit", "借", "否", "false", "0"}
TYPE_VALUE_INCOME  = {"收入", "入", "income", "in", "credit", "贷", "是", "true", "1"}
TYPE_VALUE_IGNORE  = {"不计收支", "不计", "中性交易", "neutral", "ignore", "/"}
```
> `"/"` 由**一手实测**加入（D31）：真实微信账单 `收/支` 列的中性交易值就是单个 `/`（该文件 228 行 = `支出`×176 / `收入`×48 / `/`×4，与其自述「中性交易：4笔」逐一对齐）。缺它则这 4 行被记成 `type_unresolved` 而非 `type_ignored`——**结果仍是跳过，但跳过原因失真**。

- [x] 3.1 判前对单元格值做 `strip().lower()`（中文不受影响，`True/FALSE` 受影响）
- [x] 3.2 三集合**互斥**（§4.2 断言）；命中 `IGNORE` 优先于其余两集（`不计收支` 不得因含「收支」子串误判——本实现是**全等匹配**，非子串，需在测试里钉住；`"/"` 同理：**只有单字符 `/` 全等才命中**，含斜杠的组合值如 `充值/提现` 不得被判为 IGNORE）
- [x] 3.3 `借/贷` 属于值映射而非列名别名：银行列名不内置（D6），但用户手选该列后值仍可判——在 docstring 注明此区别
- [x] 3.4 `"/"` 的来由（中性交易占位，一手实测）写进模块 docstring；**只写结构事实，禁止抄真实账单的任何交易内容**（红线 11）

## 4. 测试（新文件 `backend/tests/test_csv_values.py`）

- [x] 4.1 `parse_amount`：`¥1,234.50`→1234.5、`(12.00)`→-12.0、`１２．５`→12.5、`12.00元`→12.0、`-19.9`→-19.9、`0`→0.0（非 None）、`/` `-` `--` `""` `None` `abc`→None
- [x] 4.2 三集合互斥断言 + `不计收支` 不被拆成 expense/income（全等匹配证据）
- [x] 4.3 `TIME_FORMATS` 与 §2 常量**逐位一致**断言（防实现期漂移）
- [x] 4.4 `parse_time` 逐形态：`2026-09-24 11:07:54.617083`→`2026-09-24 11:07`、`2026-06-04 10:58:23.000`→`2026-06-04 10:58`、`...T11:07:54`、`2026/9/24`→`2026-09-24 00:00`、`2026年9月24日 8:30`→`2026-09-24 08:30`、`2026-09-24 11:07:54~2026-09-24 11:08:00`→`2026-09-24 11:07`、`2026-09-24`→`2026-09-24 00:00`
- [x] 4.5 **不猜形态断言**：`09/24/2026`、`24/09/2026`、`1727147274`、`2026-13-01`、`garbage`、`""`、`None` → 全部 `None`
- [x] 4.6 输出格式与记录 API 正则**交叉断言**：`import` `backend/app/schemas/record.py` 的 `consume_time` pattern，对 §4.4 每个产物做 `re.fullmatch`（防「清洗函数」与「入参契约」两条路径漂移，设计 §2.4）
- [x] 4.7 `resolve_type` 四态 × 三集 × 边界（0 归支出、`source=column` 空值不回落到 sign、未知 `source` 不猜）逐条断言
- [x] 4.8 纯函数无副作用证据：同一入参重复调用结果一致、不依赖当前时间/locale

## 5. 验收门槛

- [x] 5.1 新测试全绿；`import_service.py` 与本模块**零改动关联**（核验 `git status` 不含该文件——接线在 M3）
- [x] 5.2 `pytest` 全量绿；`mypy backend/app --strict` 基线零新增（新文件自身零报错）；`ruff check` clean
- [x] 5.3 `notes` 登记已知边界：歧义日期不支持、CSV 侧不做 Unix 时间戳（时区不可知，SQLite 路径既有换算不动，D15/D17）
- [x] 5.4 pathspec 精确提交：`backend/app/services/csv_values.py`、`backend/tests/test_csv_values.py`

**验收标准（设计 §2.4）**：§2.3 边界表每行都有对应断言且通过；任何无法安全归一的值返回 `None`（交 M3 跳过并计数），**绝不静默产 0 或产脏字符串**。
