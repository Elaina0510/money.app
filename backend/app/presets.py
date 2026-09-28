"""Preset category definitions (v1.4.4 M2 / 设计 §3.2).

预设分类定义的**唯一真源（SSOT）**：v1.4.4 起由 `app.main` 的本地常量迁出至此，
14 条条目与迁出前 **逐字一致**（`doc/detailed-designv1.4.4.md` §3.2），仅按任务 2.1
在每条 seed dict 内嵌 `"is_preset": 1, "source": 1`（D3：`source` = 出身标记，
1 = 系统预设或其 CoW 派生副本）。

消费方（三处，均不得自带副本常量）：
  * `app.main.init_preset_data()` —— 新库启动 seed（`Category(**cat_data)` 直落 `source=1`）；
  * `category_service.restore_default_categories()` —— 恢复默认的名称/图标/序复位与
    定制判据（设计 §3.4 步骤 4）；
  * `routers/categories.py::GET /api/categories/presets` —— D6 确认弹窗算 M 的输入。

`backend/migrate_to_v1.4.4_source.py` 迁移脚本**刻意不 import 本文件**（停服窗口须能
裸库独立执行），其内置的 14 个预设名由 `tests/test_category_source.py` 的一致性断言
与本文件钉住（沿 v1.4.3-boot2 dormant 脚本同款防漂移惯例）。
"""

from app.models.category import LEGACY_CATEGORY_TYPE

# (name, icon, sort_order)：预设分类的有序定义表——**顺序即默认排序**（贪心序尾记判据
# 按本表自上而下匹配，设计 §3.4），值与 v1.4.3 M8 起的 main.py 原 seed 逐字一致。
PRESET_SPECS: list[tuple[str, str, int]] = [
    ("餐饮", "mdi-food", 1),
    ("出行", "mdi-bus", 2),
    ("购物", "mdi-cart", 3),
    ("娱乐", "mdi-gamepad", 4),
    ("医疗", "mdi-hospital-box", 5),
    ("居住", "mdi-home", 6),
    ("通讯", "mdi-cellphone", 7),
    ("工作", "mdi-briefcase", 8),
    ("旅行", "mdi-bag-suitcase", 9),
    ("账单与费用", "mdi-receipt-text", 10),
    ("工资", "mdi-wallet", 11),
    ("红包", "mdi-gift", 12),
    ("理财", "mdi-finance", 13),
    ("其他", "mdi-cash-minus", 14),
]

# Preset categories data
# v1.4.3 M8（D11）：收支双套 15 条合并为**单套 14 条**——「其他支出/其他收入」
# 合并为「其他」（固定 mdi-cash-minus、恒末位）；type 列恒写占位值（D2 列保留语义废弃）。
# v1.4.4 M2（D3 / 任务 2.1）：seed dict 内嵌 is_preset=1 与 source=1（迁出前 main.py
# 仅有 is_preset，故本行是 §3.2 要求的唯一语义增量）。
PRESET_CATEGORIES: list[dict[str, object]] = [
    {"name": name, "type": LEGACY_CATEGORY_TYPE, "icon": icon,
     "sort_order": sort_order, "is_preset": 1, "source": 1}
    for name, icon, sort_order in PRESET_SPECS
]
