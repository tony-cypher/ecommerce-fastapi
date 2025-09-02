from fastapi import FastAPI, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from typing import Any, Callable


class EcommerceException(Exception):
    """This is the base class for all E-commerce errors"""

    pass


class InvalidToken(EcommerceException):
    """User has provided an invalid or expired token"""

    pass


class InvalidAccessToken(EcommerceException):
    """User has provided an invalid access token"""

    pass


def create_exception_handler(
    status_code: int, initial_detail: Any
) -> Callable[[Request, Exception], JSONResponse]:
    async def exception_handler(request: Request, exec: EcommerceException):
        return JSONResponse(content=initial_detail, status_code=status_code)

    return exception_handler


def register_all_errors(app: FastAPI):
    app.add_exception_handler(
        InvalidToken,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Token is invalid or expired",
                "resolution": "Please get new token",
                "error_code": "Invalid token",
            },
        ),
    )

    app.add_exception_handler(
        InvalidAccessToken,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "Access token is invalid or expired",
                "resolution": "Please get a new access token",
                "error_code": "Invalid access token",
            },
        ),
    )
