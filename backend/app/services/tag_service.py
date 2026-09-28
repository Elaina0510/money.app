"""Tag business logic."""

from datetime import datetime
from typing import Any

from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.category import Category
from app.models.tag import Tag
from app.models.user import User
from app.schemas.tag import TagCreate, TagUpdate
from app.utils.response import Code


async def get_tags(
    db: AsyncSession, current_user: User | None = None, search: str | None = None
) -> list[Tag]:
    """Get all tags visible to the user, excluding soft-deleted tags.

    v1.4.2 M5：解除原 limit(20) 硬上限，响应仍为裸数组，既有调用方零改动即拿到全量。
    """
    query = select(Tag).where(Tag.deleted_at.is_(None)).order_by(Tag.id)
    if current_user:
        query = query.where(Tag.user_id == current_user.id)
    else:
        query = query.where(Tag.user_id.is_(None))
    if search:
        query = query.where(Tag.name.contains(search))
    result = await db.exec(query)
    return list(result.all())


async def get_tags_paged(
    db: AsyncSession,
    current_user: User | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Tag], int]:
    """分页取标签，返回 (当页列表, 匹配总数)。

    v1.4.2 M5 新增：供标签管理二级页「展开更多」使用。
    过滤口径与 get_tags 完全一致（未软删 + 用户隔离），search 同时作用于
    items 与 total 两处，故 total 即「匹配总数」而非全库总数。
    """
    conds: list[Any] = [col(Tag.deleted_at).is_(None)]
    if current_user:
        conds.append(col(Tag.user_id) == current_user.id)
    else:
        conds.append(col(Tag.user_id).is_(None))
    if search:
        conds.append(col(Tag.name).contains(search))

    count_result = await db.exec(select(func.count(col(Tag.id))).where(*conds))
    total: int = int(count_result.one() or 0)

    rows = await db.exec(
        select(Tag)
        .where(*conds)
        .order_by(col(Tag.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows.all()), total


async def get_tag(
    db: AsyncSession, tag_id: int, current_user: User | None = None
) -> dict[str, Any] | None:
    """Get a single tag with its associated category.

    IDOR 防护:非归属者视为不存在(返回 None → 404)。
    """
    tag = await db.get(Tag, tag_id)
    if not tag:
        return None
    if current_user is not None and tag.user_id != current_user.id:
        return None
    category_name = None
    if tag.category_id:
        category = await db.get(Category, tag.category_id)
        if category:
            category_name = category.name
    return {
        "id": tag.id,
        "name": tag.name,
        "category_id": tag.category_id,
        "category_name": category_name,
        "created_at": tag.created_at,
    }


async def create_tag(db: AsyncSession, data: TagCreate, current_user: User | None = None) -> Tag:
    """Create a new tag, optionally with category_id."""
    # Validate category exists if provided
    if data.category_id:
        category = await db.get(Category, data.category_id)
        if not category:
            raise ValueError("关联的分类不存在")
    tag = Tag(
        name=data.name,
        category_id=data.category_id,
        user_id=current_user.id if current_user else None,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def update_tag(
    db: AsyncSession,
    tag_id: int,
    data: TagUpdate,
    current_user: User | None = None,
) -> Tag | dict[str, Any] | None:
    """Update a tag name and/or category_id."""
    tag = await db.get(Tag, tag_id)
    if not tag:
        return None

    # Ownership check
    if tag.user_id is not None and (current_user is None or tag.user_id != current_user.id):
        return {"code": Code.FORBIDDEN, "message": "无权操作"}

    update_data = data.model_dump(exclude_unset=True)
    # Validate category exists if being set
    if "category_id" in update_data and update_data["category_id"] is not None:
        category = await db.get(Category, update_data["category_id"])
        if not category:
            raise ValueError("关联的分类不存在")
    for key, value in update_data.items():
        setattr(tag, key, value)
    await db.commit()
    await db.refresh(tag)
    return tag


async def delete_tag(
    db: AsyncSession, tag_id: int, current_user: User | None = None
) -> dict[str, Any] | None:
    """Soft-delete a tag by setting deleted_at. Returns None if successful, or an error dict."""
    tag = await db.get(Tag, tag_id)
    if not tag:
        return {"code": Code.NOT_FOUND, "message": "标签不存在"}

    # Ownership check
    if tag.user_id is not None and (current_user is None or tag.user_id != current_user.id):
        return {"code": Code.FORBIDDEN, "message": "无权操作"}

    tag.deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await db.commit()
    return None


async def batch_delete_tags(db: AsyncSession, ids: list[int], current_user: User) -> int:
    """软删当前用户的一批标签；任一 id 不满足归属/存活条件则整单失败、零落删除。

    v1.4.4 M1 新增（REQ-002）。控制流三步（设计 §2.1）：
      ① 一次查询取回「归属本人 + 未软删 + 在请求 id 集内」的行（无 N+1）；
      ② 命中数 ≠ `len(set(ids))` → 抛中文 ValueError，此时尚未写任何行 → 整单零落删除；
      ③ 全命中 → 逐行置 `deleted_at`（沿单删的时间格式手法），一次 commit 单事务原子提交。

    归属口径**严于** `delete_tag`：只认 `user_id == current_user.id`，刻意不开
    `user_id IS NULL` 的全局预设行口子（红线 10）——跨用户 id 与全局 id 一律计入
    步骤 ② 的「不存在」。不写数据回溯、不发事件、无条数上限。
    """
    requested = set(ids)
    result = await db.exec(
        select(Tag)
        .where(
            col(Tag.user_id) == current_user.id,
            col(Tag.deleted_at).is_(None),
            col(Tag.id).in_(requested),
        )
        .order_by(col(Tag.id))
    )
    tags = list(result.all())

    if len(tags) != len(requested):
        raise ValueError("部分标签不存在或已被删除，请刷新后重试")

    deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for tag in tags:
        tag.deleted_at = deleted_at
    await db.commit()
    return len(tags)


async def clear_all_tags(db: AsyncSession, current_user: User) -> int:
    """软删当前用户全部未软删标签；0 条也成功返回 0（不抛错，幂等）。

    v1.4.4 M1 新增（REQ-001）。归属口径与 `batch_delete_tags` 一致：只触碰
    `user_id == current_user.id` 的行，`user_id IS NULL` 的全局预设行不在范围内
    （红线 10）。一次查询 + 一次 commit，不写数据回溯、不发事件。
    """
    result = await db.exec(
        select(Tag).where(
            col(Tag.user_id) == current_user.id,
            col(Tag.deleted_at).is_(None),
        )
    )
    tags = list(result.all())

    deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for tag in tags:
        tag.deleted_at = deleted_at
    await db.commit()
    return len(tags)
