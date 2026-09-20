"""Category Pydantic schemas."""

from pydantic import BaseModel, Field


class CategoryReorder(BaseModel):
    """Schema for batch reordering the (single) visible category list.

    v1.4.3 M8 起分类不再分收支两组：``ids`` 必须是该用户**全量**可见分类的有序 id
    （缺一即 400，见 service 校验）；「其他」无论提交落点均由服务端强制归一化到末位。
    """

    ids: list[int]


class CategoryCreate(BaseModel):
    """Schema for creating a new category.

    v1.4.3 M8（D2）：不再收 ``type``——分类收支共用；旧客户端多带的 type 字段由
    pydantic 默认忽略（模型字段无 extra 配置时未知字段 ignore）。
    """

    name: str = Field(..., min_length=1, max_length=50)
    icon: str = Field(default="mdi-cash", max_length=50)
    # None → 服务端计算（追加到全列表末尾、「其他」之前）；显式传入则原样写入（向后兼容）
    sort_order: int | None = Field(default=None, ge=0)


class CategoryUpdate(BaseModel):
    """Schema for updating an existing category."""

    name: str | None = Field(default=None, min_length=1, max_length=50)
    icon: str | None = Field(default=None, max_length=50)
    # 字段定义保留（避免旧客户端 422 语义变化），v1.4.2 起服务层一律忽略
    sort_order: int | None = Field(default=None, ge=0)


class CategoryResponse(BaseModel):
    """Schema for category response.

    ``type`` 字段保留（列原值，供事后排查）；前端自 v1.4.3 起不再读取。
    """

    id: int
    name: str
    type: str
    icon: str
    sort_order: int
    is_preset: int
    created_at: str
