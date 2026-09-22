# M1 - 分类拖拽排序永远可用（需求一）

> 对应需求一（设计 §一）。去除「非末位即整体禁用」的锁定逻辑 + 后端 reorder「必须有其他行」硬校验，「其他家族」前后端归一化强制置尾——任何数据态拖拽都可用，不以数据干净为前提（D1）。
> 涉及文件：`backend/app/services/category_service.py`（:14-27、:78-92、:149-153、:243-275）、`frontend/src/pages/SettingsCategoriesPage.vue`、`backend/tests/test_categories_reorder.py`、`frontend/src/pages/SettingsSubPages.test.js`。
> 依赖：无。与 M3 同文件（`category_service.py`）不同函数区域，**串行提交 M1 → M3**（§0.2）。与 M2 共享「其他家族」字面值常量，各自定义 + 一致性断言防漂移（沿 v1.4.3 惯例）。

---

## 1. 根因复核（设计 §1.2.0，先复现后改·红线）

- [x] 1.1 在**现场库副本**（`backend/money.db` 拷贝，只读）取证确认分支 A 形态：「其他」`sort_order=14`、「其他支出」「其他收入」两预设行 `sort_order=99` 压其后 → 「其他」非末位 → `isOtherLocked` 整列表禁用。取证已闭环（§1.2.0），本步核验副本形态与描述一致即可，**不回写真实库**
- [ ] 1.2 记录二次确认口径：若服务器现场库与副本形态不同（发布窗口冒烟时），按判定树 B（其他在末位仍不能拖）/ C（能拖但保存失败）手法补查——**属新信息则停下向用户确认，不猜**
- [x] 1.3 确认无论落入哪支，§2–§3 改造都实施（D1）

## 2. 后端：家族判据 + 置尾归一化（设计 §1.2.1）

- [x] 2.1 `category_service.py` 顶部新增常量：`OTHER_CATEGORY_NAME = "其他"`、`LEGACY_OTHER_NAMES = ("其他支出", "其他收入")`、`OTHER_FAMILY_RANK: dict[str,int] = {"其他支出":0, "其他收入":1, "其他":2}`（:14-27）
- [x] 2.2 `_is_other_category(cat)` 签名不变，判据改 `cat.name in OTHER_FAMILY_RANK`；新增 `_is_other_row(name: str)` 同判据
- [x] 2.3 `reorder_categories`（:243-275）：删除「缺少其他 → ValueError」两行（:262-263，D8）；置尾归一化改为 `ordered = 非家族(提交序) + 家族(按 OTHER_FAMILY_RANK 稳定排序)`（:267-268 原单名拼接替换）；全量匹配校验（:260-261）**保留**为唯一防漏位守门
- [x] 2.4 `_next_sort_order`（:78-92）：钳制对象「其他单行」→「家族最小 sort 的行」（`min(家族行, key=sort_order)`）；无家族行时 `max+1` 不变；补下钳 `max(base+1, 0)` 防负值（脏数据态 min-1 可能 ≤0）
- [x] 2.5 `update_category` 禁改名（:149-153）：仅「其他」本名维持不可改；旧名两行允许改名（改出家族即普通行）——核查现判据若用家族需收窄回本名
- [x] 2.6 `_visible_categories` / `get_categories` 不动（核验）

## 3. 前端：删锁定 + 镜像归一（设计 §1.2.2）

- [x] 3.1 `SettingsCategoriesPage.vue` script 新增 `OTHER_CATEGORY_NAME`/`LEGACY_OTHER_NAMES`/`OTHER_FAMILY_RANK`（与后端同表）+ `isOtherFamily(cat)`（`Object.hasOwn(OTHER_FAMILY_RANK, cat.name)`）
- [x] 3.2 **删除** `isOtherLocked()` 整函数（:198-201）与模板 `:disabled="isOtherLocked(dragList)"` 绑定（:41）——Draggable 不再有禁用态
- [x] 3.3 把手条件（模板 :55-58）定为 `cat.name !== OTHER_CATEGORY_NAME`：仅「其他」无把手（占位），旧名两行照常给把手可拖（D7；注意**不是** `isOtherFamily`——那样旧名行也丢把手，与 D7 相反）
- [x] 3.4 `onDragEnd`（:221-229）本地镜像改写：新增 `normalizeTail(list)`（非家族保序 + 家族按名次稳定排序置尾），与后端 §2.3 **逐位一致**；`onDragEnd = normalizeTail(dragList) → submitReorder`
- [x] 3.5 `submitReorder` 失败回滚链路（快照恢复 + 静默重拉 :231-241）与 store `reorderCategories`（useCategoriesStore :64-75）**零改动**（核验）
- [x] 3.6 组件注释写入过渡态观感说明：拖动其它行松手后家族行可能「跳回」尾部，与后端落库序一致，无保存后二次跳变

## 4. 边界与异常（设计 §1.3，代码走查 + 用例覆盖）

- [x] 4.1 可见集合无「其他」只有旧名 → 可拖可保存、家族按名次置尾（原实现此态死锁，D8 已删）
- [x] 4.2 三名齐全现场态 → 家族整体置尾、「其他」恒最后
- [x] 4.3 用户显式创建「其他支出」→ 允许创建、落位家族前、归一化计入家族置尾（接受，无数据破坏）
- [x] 4.4 导入建的 sort=0 散行 → 首次成功 reorder 整体归一 1..n（既有行为）
- [x] 4.5 reorder 提交与可见集合不一致（并发新增）→ 全量校验拒绝 → 前端回滚 + 重拉真值重试即成（既有链路）
- [x] 4.6 预设行 reorder → CoW 落用户副本（`_set_sort_order` :205-240 不动）

## 5. 测试（设计 §1.4 + 附录 B）

**后端 pytest（`test_categories_reorder.py` 增改）：**
- [x] 5.1 改写「可见集合缺少『其他』→ ValueError」组 → 断言**正常保存**且家族按名次置尾（附录 B）
- [x] 5.2 保留「其他强制末位」单名组（家族判据覆盖单名态），新增三名并存组：任意乱序提交 → 落库尾段恒 `[…其他支出, 其他收入, 其他]`，非家族保持提交序
- [x] 5.3 新增 `_next_sort_order` 家族钳制三态（有旧名无「其他」/三名齐全/无家族）+ 下钳 0 用例
- [x] 5.4 常量一致性：`category_service.OTHER_FAMILY_RANK.keys()` ⊇ 且 ⊆ `migrate_to_v1.4.3boot2_categories` 脚本侧常量（M2 落文件后此用例才可 import；M1 先行时以 `pytest.importorskip`/标记处理，M2 合入后转实断言）
  > **实测修正（M1，2026-09-22）**：`pytest.importorskip("migrate_to_v1.4.3boot2_categories")` 对**含点号**的脚本文件名不可用——import 机制把 dots 当包分隔符，抛 `SyntaxError` 而非 `ImportError`，起不到 skip 作用。等价实现：先探测 `backend/migrate_to_v1.4.3boot2_categories.py` 是否存在，不存在即 `pytest.skip`（skip 而非删用例），存在则按 `test_migration_v143.py` 的 `spec_from_file_location` 路径加载后做双侧常量一致实断言。**M2 落文件后本用例自动由 skip 转实断言，M2 无需再改。**
- [x] 5.5 既有用例回归：全量匹配校验、CoW 不写脏预设。**审查补入**：测试预设含旧名行「其他收入」（`conftest.py:41`），家族判据下其被名次置尾——:53-77/:80-107/:111-129/:273 等位次/次序断言受影响的用例均属合法改写范围（仅调受影响断言维度、其余零丢失）；文件头 :4-13「旧名不判为其他」注释随改写同步更新
  > **实测补充（M1，2026-09-22）**：同一夹具家族行还波及 **`backend/tests/test_categories.py`**（任务 §涉及文件 未点名）——`test_create_without_sort_order_appends_before_other` / `test_no_other_category_appends_at_tail` / `test_sort_order_single_list_no_longer_partitioned_by_legacy_group` / `test_update_custom_category_renames_ok` / `test_sort_isolation_between_users` 5 例的 sort 断言由家族钳制改写（前 1 例按新口径改断言，后 4 例加「先清夹具家族行构造无家族态」前置以隔离各自原主题，断言值零改动）。与 5.5 同口径（仅调受影响维度、零删除），已随本模块一并改写提交。

**前端 vitest（`SettingsSubPages.test.js`）：**
- [x] 5.6 删 `isOtherLocked` 组（:409-413）与 `disabled` prop 断言（**实测两处：:347 用例2b + :413 用例2b-2**，审查补入）→ 替换为「任何数据态 disabled 恒 undefined/false」（删 `:disabled` 绑定后为 undefined）
- [x] 5.7 `isOther` 真值表（:399-407 断言旧名不命中）**反转**：家族判定改 `isOtherFamily` 命中断言 + 新增 `isOther`（仅本名，控把手）真值表
- [x] 5.8 `onDragEnd` 归一化（:380-397 现例）改写为名次置尾版本：家族乱序输入 → 名次置尾输出；仅「其他」在中间 → 回尾部
- [x] 5.9 把手渲染 `?raw` 断言：旧名两行 `.drag-handle` 在场、「其他」行 `.drag-handle-placeholder`
- [x] 5.10 保存失败回滚 + 重拉既有用例保持；「v1.4.3 M9 分类拖拽 flip 让位动画」组（:1697-1779，含 :1763 onDragEnd 零闪回断言）**整组复跑通过**为 M1 回归核查点（若红先核对归一化口径，不回退 M9 参数）

## 6. 验收门槛

- [x] 6.1 `pytest backend/tests/test_categories_reorder.py` 全绿；`npm test` 相关组全绿；mypy/ruff 基线零新增
  > 实测（2026-09-22）：`pytest tests/test_categories_reorder.py` 19 passed / 1 skipped（skip = M2 脚本常量一致性占位）；全量 `pytest tests/` **252 passed + 1 skipped**（基线 245 passed，零失败）；`npm test` **390 passed / 15 files**（基线 389，只增不减）；`mypy app/` **90 errors in 14 files**（= 基线，改动函数零报错）；`ruff check app/ tests/` All checks passed；`npm run lint` 0 errors / 2 warnings（= 基线，CsvMappingDialog 既有）。
- [ ] 6.2 人工·明暗主题 × 竖/宽屏实测拖拽（触摸长按 150ms、鼠标即拖）、保存后无跳变、toast 文案不变
- [ ] 6.3 人工·现场库副本实测「其他」非末位态可拖
- [x] 6.4 不回退核验：v1.4.3 M8 分类收支共用单列表、§8.2「其他」置尾恒等式、boot M9 拖拽动画参数（delay/animation/把手维持现状，不触碰 vuedraggable/sortablejs 既有参数）

**验收标准（设计 §1.4）**：把手按压必有拖拽反馈（任何数据态）；松手即保存成功；重进页面顺序与松手时一致（「其他」恒末位）。
