"""金额处理工具。

记账场景金额统一保留两位小数,避免 float 累计误差
(如 0.1 + 0.2 = 0.30000004)在聚合统计与响应中显示。

存储仍用 float(SQLite REAL),在所有"出/入"边界统一 round。
"""


def round_money(value) -> float:
    """把任意数值(含 None/str)规整为两位小数的 float。"""
    if value is None:
        return 0.0
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0
