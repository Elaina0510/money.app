"""Category Pydantic schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class CategoryReorder(BaseModel):
    """Schema for M3 batch reordering one type group (full ordered id list).

    ``ids`` 必须是该用户该类型可见分类的全量 id（缺一即 400，见 service 校验）；
    「其他」无论提交落点均由服务端强制归一化到末位。
    """

    type: Literal["expense", "income"]
    ids: list[int]


class CategoryCreate(BaseModel):
    """Schema for creating a new category."""

    name: str = Field(..., min_length=1, max_length=50)
    type: str = Field(..., pattern=r"^(income|expense)$")
    icon: str = Field(default="mdi-cash", max_length=50)
    # None → 服务端计算（追加到分组末尾、「其他」之前）；显式传入则原样写入（向后兼容）
    sort_order: int | None = Field(default=None, ge=0)


class CategoryUpdate(BaseModel):
    """Schema for updating an existing category."""

    name: str | None = Field(default=None, min_length=1, max_length=50)
    icon: str | None = Field(default=None, max_length=50)
    # 字段定义保留（避免旧客户端 422 语义变化），v1.4.2 起服务层一律忽略
    sort_order: int | None = Field(default=None, ge=0)


class CategoryResponse(BaseModel):
    """Schema for category response."""

    id: int
    name: str
    type: str
    icon: str
    sort_order: int
    is_preset: int
    created_at: str
