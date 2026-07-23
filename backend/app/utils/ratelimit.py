"""内存滑动窗口频率限制。

用于保护登录/注册等开放端点,防止暴力破解与注册轰炸。
基于进程内字典 + 滑动窗口计数,无外部依赖。

局限:多 worker / 多进程部署时,每个 worker 各有独立计数器,
实际限额会放宽到 N×(limit)。当前部署为单 worker uvicorn,无此问题;
若未来多进程部署需精确限额,应换用 Redis 等共享存储。
"""

import time
from collections import deque
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status

# key: (route_tag, client_ip) -> deque[timestamp]
_buckets: dict[tuple[str, str], deque[float]] = {}


def _client_ip(request: Request) -> str:
    # 当前部署无反向代理,request.client.host 即真实客户端 IP。
    # 若未来引入 nginx,需改为读取 X-Forwarded-For。
    return request.client.host if request.client else "unknown"


def _check(route_tag: str, ip: str, limit: int, window: float) -> None:
    now = time.monotonic()
    key = (route_tag, ip)
    bucket = _buckets.get(key)
    if bucket is None:
        bucket = deque()
        _buckets[key] = bucket

    # 丢弃过期时间戳
    while bucket and now - bucket[0] > window:
        bucket.popleft()

    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="操作过于频繁,请稍后再试",
        )
    bucket.append(now)


def rate_limit(
    route_tag: str, limit: int = 5, window: float = 60.0
) -> Callable[[Request], Awaitable[None]]:
    """FastAPI 依赖:限制每个 IP 在 window 秒内最多 limit 次调用。

    用法:
        @router.post("/login")
        async def login(_: None = Depends(rate_limit("login", 5, 60)), ...):
    """

    async def _dependency(request: Request) -> None:
        _check(route_tag, _client_ip(request), limit, window)

    return _dependency
