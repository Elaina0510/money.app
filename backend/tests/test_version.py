"""M4（v1.4.4）版本单一真值源用例 —— 任务文件 §4.1.1–4.1.3 三条编号用例。

口径（设计 §5.1 / D4 / REQ-008）：版本号唯一定义于 `app.constants.APP_VERSION`，
经**无鉴权** `GET /api/version` 下发，前端「关于」页只读该接口、零硬编码版本字面量。

本文件除三条编号用例外，另附两条收敛面自证（任务 §1.4 删兜底键 + §5.3 全仓版本字面量
收敛），均为**新增断言**，不改动、不放宽任何既有用例。
"""

import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app import main as main_module
from app.constants import APP_VERSION
from app.routers import version as version_router

pytestmark = pytest.mark.asyncio

# 任务 §4.1.3 的「openapi 元数据同源」落点：main.py 的 FastAPI 构造参数
MAIN_SOURCE = Path(main_module.__file__).read_text(encoding="utf-8")


async def test_case_4_1_1_version_endpoint_returns_app_version(anon_client: AsyncClient) -> None:
    """§4.1.1：GET /api/version → 200、code==0、data.version 与 constants.APP_VERSION 逐字等。"""
    resp = await anon_client.get("/api/version")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"] == {"version": APP_VERSION}
    assert body["data"]["version"] == APP_VERSION
    assert isinstance(body["data"]["version"], str)
    # 统一外壳三键齐备（沿 utils/response.py 契约）
    assert set(body.keys()) == {"code", "message", "data"}


async def test_case_4_1_2_version_endpoint_is_public_no_auth(anon_client: AsyncClient) -> None:
    """§4.1.2：未登录（无 Authorization 头）→ 200，即「无鉴权」口径。"""
    assert "Authorization" not in anon_client.headers

    resp = await anon_client.get("/api/version")
    assert resp.status_code == 200
    assert resp.json()["code"] == 0

    # 路由层无鉴权依赖：version.router 全部路由的 dependencies 为空
    # （即不经 require_auth，也不依赖任何带鉴权的 Depends）
    assert version_router.router.routes
    for route in version_router.router.routes:
        assert route.dependencies == []

    # 带 token 同样 200（登录态与非登录态等价，前端无需为版本接口做分支）
    resp_with_token = await anon_client.get(
        "/api/version", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp_with_token.status_code == 200


async def test_case_4_1_3_fastapi_metadata_version_from_constants() -> None:
    """§4.1.3：FastAPI 元数据版本与 constants 同源（openapi info.version == APP_VERSION）。"""
    # 1) 真实 app 实例（main.py 构造）
    assert main_module.app.version == APP_VERSION
    # 2) openapi() 的 info.version 亦同源（文档页 /docs 显示的就是它）
    assert main_module.app.openapi()["info"]["version"] == APP_VERSION
    # 3) 同款构造参数直取：version=APP_VERSION 传进 FastAPI 构造即生效
    assert FastAPI(version=APP_VERSION).version == APP_VERSION


async def test_main_py_has_no_hardcoded_version_literal() -> None:
    """任务 §1.3/1.4 + §5.3 收敛自证：main.py 内不再有任何 `"x.y.z"` 版本字面量。

    改动前三处漂移点（FastAPI 构造参数、root 无 dist 兜底响应键）现均归一：
    构造参数走 `version=APP_VERSION`，兜底响应删版本键。
    """
    assert re.search(r'version\s*=\s*"[0-9]+\.[0-9]+\.[0-9]+"', MAIN_SOURCE) is None
    assert re.search(r'"version":\s*"[0-9]+\.[0-9]+\.[0-9]+"', MAIN_SOURCE) is None
    # 逐字复核原两处字面量已消失（用正则承载，本文件自身不留版本字面量、不污染 §5.3 grep 自证）
    assert re.search(r"1[.-]1[.-]0|1[.-]0[.-]0", MAIN_SOURCE) is None
    # 四个单行动作在场（include_router / 两处 import / 参数替换 / 删键）
    assert "app.include_router(version.router)" in MAIN_SOURCE
    assert "from app.constants import APP_VERSION" in MAIN_SOURCE
    assert "version=APP_VERSION" in MAIN_SOURCE
    # M2 笔次未回退（设计 §0.2 注：main.py 上 M2 → M4 顺序合入、互不冲突）
    assert "from app.presets import PRESET_CATEGORIES" in MAIN_SOURCE


async def test_root_fallback_response_drops_version_key(
    anon_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """任务 §1.4：无 dist 兜底的 root 响应删掉版本键后仍 200，其余键不丢。"""
    monkeypatch.setattr(main_module, "FRONTEND_DIST", Path("./__no_such_dist_dir__"))

    resp = await anon_client.get("/")

    assert resp.status_code == 200
    body = resp.json()
    assert "version" not in body
    assert body == {"message": "Money App API", "docs": "/docs"}
