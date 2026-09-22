"""Budget Pydantic schemas (v1.4.3 M12 命名预算模型)."""

from typing import Literal

from pydantic import BaseModel, Field

# 范围模式（D3）：include = 仅计入所选分类，**空集 = 动态全部分类**（v1.4.3-boot2 M3）；
# exclude = 所选分类不计入（空集同样 = 全部分类）
ScopeMode = Literal["include", "exclude"]


class BudgetCreate(BaseModel):
    """Schema for creating a named budget (纯创建，任务 2.2).

    v1.4.3 M12 起 POST 不再是 upsert：同月同名的多条预算各自独立成行。
    ``name`` 1–50 必填、``amount`` > 0 由 pydantic 直接 422；
    ``scope_mode`` 非法值同样 422（Literal 约束）；
    服务层只校验名称/金额/月份/分类 id 合法性。

    v1.4.3-boot2 M3（决策 D3，任务 2.2）：**「include → 分类去重后 ≥1」校验已删除**
    ——``category_ids`` 为空现在两种模式都合法，include 空集即「动态全部分类」
    （后续新增分类自动计入）。两种空集（主动不选 / 关联分类被删光）由
    ``budgets.dormant`` 列区分，而非由载荷表达：``dormant`` **不在请求体契约内**
    （只由分类删除级联置 1、由成功保存清 0），但出现在响应里
    （BudgetDetail 增 ``dormant: bool``）。
    """

    month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    name: str = Field(..., min_length=1, max_length=50)
    amount: float = Field(..., gt=0, le=99999999.99)
    scope_mode: ScopeMode = Field(default="include")
    # 顺序不敏感（服务层去重后按分类自身排序落库）；**两种模式都允许空列表**（M3/D3）
    category_ids: list[int] = Field(default_factory=list)


class BudgetUpdate(BaseModel):
    """Schema for updating an existing budget（全字段编辑，任务 2.3）.

    ``month`` **不可改**：故意不声明该字段，pydantic 默认 ignore 未知字段，
    故旧客户端多带的 month 一律被忽略（不报错、不落库）。

    唤醒语义（v1.4.3-boot2 M3 任务 3.5 / 决策 D9）：PUT **成功即 ``dormant=0``**，
    故休眠预算重选分类、或干脆一个都不选（= 动态全部）、或改 scope_mode=exclude
    都是恢复计入统计的正路；请求体不接受 ``dormant`` 字段（服务端专属列）。
    """

    name: str = Field(..., min_length=1, max_length=50)
    amount: float = Field(..., gt=0, le=99999999.99)
    scope_mode: ScopeMode = Field(default="include")
    category_ids: list[int] = Field(default_factory=list)
