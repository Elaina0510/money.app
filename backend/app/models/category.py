"""Category model."""

from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint

# v1.4.3 M8（D2）：分类不再区分收支，`type` 列保留原值仅供事后排查，
# 语义在代码层彻底废弃；新建行恒写占位值 LEGACY_CATEGORY_TYPE。
# 认知登记（任务 1.3）：SQLModel 的 UniqueConstraint 不生成命名索引对象
# （真库仅 sqlite_autoindex_categories_N），新库 create_all 直接产出表级内嵌
# UNIQUE (name, user_id)；旧库换形由迁移脚本整表重建完成，不可用 DROP INDEX。

# 新行 type 占位值（列保留、语义废弃）——服务层/迁移脚本统一引用，勿散落字面量
LEGACY_CATEGORY_TYPE = "expense"


class Category(SQLModel, table=True):
    """Category model: one shared tag set for both income and expense records."""

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("name", "user_id", name="idx_categories_name_user"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(
        default=None, nullable=True, foreign_key="users.id", ondelete="CASCADE"
    )
    name: str = Field(nullable=False)
    # 废弃语义列（D2）：保留原值供事后排查，新行恒写 LEGACY_CATEGORY_TYPE
    type: str = Field(default=LEGACY_CATEGORY_TYPE, nullable=False)
    icon: str = Field(default="mdi-cash", nullable=False)
    sort_order: int = Field(default=0, nullable=False)
    is_preset: int = Field(default=0, nullable=False)  # 0=custom, 1=preset
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
