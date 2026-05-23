"""Authentication API router: register, login, user info."""

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlmodel import SQLModel, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_session
from app.models.budget import Budget
from app.models.category import Category
from app.models.record import Record
from app.models.tag import Tag
from app.models.user import User
from app.schemas.user import TokenResponse, UserInfo, UserLogin, UserRegister
from app.utils.auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.utils.response import Code, error_response, success_response

router = APIRouter(prefix="/api/auth", tags=["用户认证"])


async def _migrate_orphan_data(db: AsyncSession, user_id: int):
    """Assign orphan data (user_id IS NULL) to the first registered user."""
    tables: list[type[SQLModel]] = [Record, Budget, Category, Tag]
    for table in tables:
        stmt = select(table).where(table.user_id.is_(None))  # type: ignore[attr-defined]
        result = await db.exec(stmt)
        orphans = list(result.all())
        for row in orphans:
            row.user_id = user_id
    await db.commit()


@router.post("/register")
async def register(
    data: UserRegister,
    db: AsyncSession = Depends(get_session),
):
    """Register a new user."""
    # Check if username already exists
    stmt = select(User).where(User.username == data.username)
    result = await db.exec(stmt)
    existing = result.first()
    if existing:
        return error_response(Code.CONFLICT, "用户名已存在")

    # Check if this is the first user
    count_stmt = select(func.count(User.id))
    count_result = await db.exec(count_stmt)
    user_count = count_result.one()
    is_first_user = user_count == 0

    user = User(
        username=data.username,
        hashed_password=get_password_hash(data.password),
    )
    db.add(user)
    await db.flush()

    # First user inherits all orphan data
    if is_first_user:
        await _migrate_orphan_data(db, user.id)

    await db.commit()
    await db.refresh(user)

    # Generate token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=access_token_expires,
    )

    return success_response(
        data=TokenResponse(
            access_token=access_token,
            username=user.username,
            user_id=user.id,
        ).model_dump(),
        message="注册成功",
    )


@router.post("/login")
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_session),
):
    """Login and get access token."""
    stmt = select(User).where(User.username == data.username)
    result = await db.exec(stmt)
    user = result.first()

    if not user or not verify_password(data.password, user.hashed_password):
        return error_response(Code.PARAM_ERROR, "用户名或密码错误", status_code=401)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=access_token_expires,
    )

    return success_response(
        data=TokenResponse(
            access_token=access_token,
            username=user.username,
            user_id=user.id,
        ).model_dump(),
        message="登录成功",
    )


@router.get("/me")
async def get_me(
    current_user: User | None = Depends(get_current_user),
):
    """Get current user info (returns None if not logged in)."""
    if current_user is None:
        return success_response(data=None)
    return success_response(
        data=UserInfo(id=current_user.id, username=current_user.username).model_dump()
    )
