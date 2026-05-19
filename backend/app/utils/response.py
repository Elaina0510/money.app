"""Unified response format and error codes."""

from typing import Any

from fastapi.responses import JSONResponse


# Error codes
class Code:
    SUCCESS = 0
    PARAM_ERROR = 40001
    NOT_FOUND = 40002
    CONFLICT = 40003
    FILE_INVALID = 40004
    SERVER_ERROR = 50001


CODE_MESSAGES: dict[int, str] = {
    Code.SUCCESS: "success",
    Code.PARAM_ERROR: "参数验证错误",
    Code.NOT_FOUND: "资源不存在",
    Code.CONFLICT: "操作冲突",
    Code.FILE_INVALID: "文件违规",
    Code.SERVER_ERROR: "服务器内部错误",
}


def success_response(data: Any = None, message: str | None = None) -> JSONResponse:
    """Return a successful unified response."""
    return JSONResponse(
        content={
            "code": Code.SUCCESS,
            "message": message or CODE_MESSAGES[Code.SUCCESS],
            "data": data,
        }
    )


def error_response(
    code: int,
    message: str | None = None,
    data: Any = None,
    status_code: int = 400,
) -> JSONResponse:
    """Return an error unified response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message or CODE_MESSAGES.get(code, "未知错误"),
            "data": data,
        },
    )
