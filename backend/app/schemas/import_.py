"""Import request schemas."""

from pydantic import BaseModel, Field


class CategoryMappingItem(BaseModel):
    """Single category mapping item."""

    action: str = Field(..., pattern="^(map|create)$")
    target_id: int | None = None  # Required when action="map"
    type: str | None = None  # Required when action="create" (expense/income)


class TagMappingItem(BaseModel):
    """Single tag mapping item."""

    action: str = Field(..., pattern="^(map|create)$")
    target_id: int | None = None  # Required when action="map"
    category_id: int | None = None  # Required when action="create"


class ImportCsvRequest(BaseModel):
    """CSV import confirm request body.

    v1.4.3-boot3 §3.2（D18）：`columns` / `type_source` / `fallback_category` **全可选**，
    `category_mapping` / `tag_mapping` 由必填改为**默认空 dict**（微信账单无分类列时前端
    可只发 `fallback_category`）→ 旧前端不发新字段也能跑。
    必需角色缺失、列索引越界等业务校验**不放这里**（Pydantic 抛 422 时前端拦截器读不到
    `detail`，设计 §0.4-8），一律由 service 抛中文 `ValueError` 经路由转 `PARAM_ERROR`。

    v1.4.4 V2：`columns` 的值放宽为 `int | list[int]`——**只有 `note` 用得到 list**
    （一个文件的备注可来自多列：微信 `交易对方` + `商品`）。单值 `int` 载荷**继续有效**
    （D18 向后兼容：本轮前端未更新）。越界校验对 list **逐元素**做，中文文案口径不变。
    """

    cache_id: str
    format: str = Field(
        ..., pattern="^(native|cashew|cashew_template|alipay|wechat|custom)$"
    )
    # 角色 → 列索引（`note` 可为多列，V2）；缺省 = 后端按方言自行推导
    columns: dict[str, int | list[int]] | None = None
    type_source: str | None = Field(
        None, pattern="^(column|sign|all_expense|all_income)$"
    )
    fallback_category: CategoryMappingItem | None = None  # 无分类列 / 分类名落空时的默认归入
    category_mapping: dict[str, CategoryMappingItem] = {}
    tag_mapping: dict[str, TagMappingItem] = {}


class ImportSqlRequest(BaseModel):
    """SQL import confirm request body."""

    cache_id: str
    format: str = Field(..., pattern="^(text_sql|sqlite_binary)$")
    is_third_party: bool = False
    merge_mode: str = Field(default="insert_all", pattern="^insert_all$")
    category_mapping: dict[str, CategoryMappingItem] | None = None
    tag_mapping: dict[str, TagMappingItem] | None = None
