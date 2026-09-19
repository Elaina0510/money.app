"""Quick Template model for manually added quick-accounting templates."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class QuickTemplate(SQLModel, table=True):
    """Quick template for manually added quick-accounting shortcuts."""

    __tablename__ = "quick_templates"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(
        default=None, nullable=True, foreign_key="users.id", ondelete="CASCADE"
    )
    tag_id: int | None = Field(
        default=None, nullable=True, foreign_key="tags.id", ondelete="SET NULL"
    )
    category_id: int | None = Field(
        default=None, nullable=True, foreign_key="categories.id", ondelete="SET NULL"
    )
    type: str = Field(nullable=False)  # "expense" / "income"
    amount: float = Field(nullable=False)
    # v1.4.2 M6（D4）：manual=手动模板（默认，旧行经迁移脚本回填）
    # auto_ignored=自动模板忽略签名（仅 tag_id/type/amount 三要素有效，category_id 恒为 None）
    kind: str = Field(default="manual", max_length=20, nullable=False)
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
