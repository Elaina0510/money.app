"""Budget models for monthly named budgets (v1.4.3 M12)."""

from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint

# v1.4.3 M12（决策 D3）：预算由「每 (分类,月) 一条」改「某自然月下的具名预算」——
# 同月可多条、名称同月不强制唯一，作用范围改由 budget_categories 关联表表达。
# 认知登记（沿 M8 / 设计 §8.1）：SQLModel 的 UniqueConstraint 不生成命名索引对象
# （真库仅 sqlite_autoindex_budget_categories_N），旧库换形由迁移脚本阶段 B 整表
# 重建完成，不可用 DROP INDEX；新 budgets 已无任何表级 UNIQUE（多条同月合法）。

# 范围模式常量（服务层校验与迁移脚本统一引用，勿散落字面量）
SCOPE_INCLUDE = "include"
SCOPE_EXCLUDE = "exclude"
SCOPE_MODES: tuple[str, str] = (SCOPE_INCLUDE, SCOPE_EXCLUDE)

# 迁移产出的「未知分类」只读态预算名（设计 §12.2.6 第 2 步）
UNKNOWN_CATEGORY_NAME = "未知分类"


class Budget(SQLModel, table=True):
    """某自然月下的一条具名预算（同月可多条）。"""

    __tablename__ = "budgets"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(
        default=None, nullable=True, foreign_key="users.id", ondelete="CASCADE"
    )
    name: str = Field(nullable=False)  # 预算名称；同月不强制唯一（任务 1.1）
    month: str = Field(nullable=False)  # YYYY-MM format（PUT 不可改，任务 2.3）
    amount: float = Field(nullable=False)  # Budget amount
    scope_mode: str = Field(default=SCOPE_INCLUDE, nullable=False)  # include | exclude
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )


class BudgetCategory(SQLModel, table=True):
    """预算 ↔ 分类关联表：include 语义为「仅计入这些分类」，
    exclude 语义为「这些分类不计入」（空集合 = 全部分类）。
    """

    __tablename__ = "budget_categories"
    __table_args__ = (
        UniqueConstraint("budget_id", "category_id", name="idx_budgetcat_budget_category"),
    )

    id: int | None = Field(default=None, primary_key=True)
    budget_id: int = Field(
        nullable=False, foreign_key="budgets.id", ondelete="CASCADE"
    )
    category_id: int = Field(nullable=False, foreign_key="categories.id")
