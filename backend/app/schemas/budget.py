"""Budget Pydantic schemas (v1.4.3 M12 命名预算模型)."""

from typing import Literal

from pydantic import BaseModel, Field

# 范围模式（D3）：include = 仅计入所选分类；exclude = 所选分类不计入（空集合 = 全部分类）
ScopeMode = Literal["include", "exclude"]


class BudgetCreate(BaseModel):
    """Schema for creating a named budget (纯创建，任务 2.2).

    v1.4.3 M12 起 POST 不再是 upsert：同月同名的多条预算各自独立成行。
    ``name`` 1–50 必填、``amount`` > 0 由 pydantic 直接 422；
    ``scope_mode`` 非法值同样 422（Literal 约束）；
    「include → 分类去重后 ≥1」属**服务层**校验（任务 1.3）→ PARAM_ERROR。
    """

    month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    name: str = Field(..., min_length=1, max_length=50)
    amount: float = Field(..., gt=0, le=99999999.99)
    scope_mode: ScopeMode = Field(default="include")
    # 顺序不敏感（服务层去重后按分类自身排序落库）；exclude 允许空列表
    category_ids: list[int] = Field(default_factory=list)


class BudgetUpdate(BaseModel):
    """Schema for updating an existing budget（全字段编辑，任务 2.3）.

    ``month`` **不可改**：故意不声明该字段，pydantic 默认 ignore 未知字段，
    故旧客户端多带的 month 一律被忽略（不报错、不落库）。
    """

    name: str = Field(..., min_length=1, max_length=50)
    amount: float = Field(..., gt=0, le=99999999.99)
    scope_mode: ScopeMode = Field(default="include")
    category_ids: list[int] = Field(default_factory=list)
