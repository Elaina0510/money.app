"""Category model."""

from datetime import datetime

from sqlalchemy import Column, Integer
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
    # v1.4.4 M2（D3）：出身标记。1 = 系统预设或其 CoW 派生副本；0 = 用户自建。
    # 与 `is_preset`（「是否全局预设行」）**语义正交**：副本 is_preset=0 而 source=1，
    # 徽章口径由此承载（设计 §3.1）；存量库该列由 backend/migrate_to_v1.4.4_source.py
    # 以 ALTER TABLE ... ADD COLUMN source INTEGER NOT NULL DEFAULT 0 补加并回填。
    source: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
