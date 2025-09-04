from fastapi import Request, Depends
from fastapi.security import HTTPBearer
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session
from src.db.models import RefreshToken
from src.errors import (
    InvalidToken,
    InvalidAccessToken,
    InvalidRefreshToken,
    AccessTokenRequired,
    UserNotFound,
)
from .utils import decode_token
from .service import UserService


user_service = UserService()


async def is_token_revoked(jti: str, session: AsyncSession) -> bool:
    result = await session.exec(select(RefreshToken).where(RefreshToken.jti == jti))
    token = result.one_or_none()

    return not token or token.revoked


class TokenBearer(HTTPBearer):
    def __init__(self, auto_error=True):
        super().__init__(auto_error=auto_error)

    async def __call__(
        self, request: Request, session: AsyncSession = Depends(get_session)
    ) -> dict:
        creds = await super().__call__(request)
        token = creds.credentials
        token_data = decode_token(token)

        if not self.token_valid(token):
            raise InvalidToken()

        await self.verify_token_data(token_data, session)

        return token_data

    def token_valid(self, token: str) -> bool:
        token_data = decode_token(token)
        return token_data is not None

    async def verify_token_data(self, token_data: dict, session: AsyncSession):
        raise NotImplementedError("Override this method in a subclass.")


# Accepts only Access token, Throws an error if access token is not provided
class AccessTokenBearer(TokenBearer):
    async def verify_token_data(self, token_data: dict, session: AsyncSession) -> None:
        if token_data and token_data["refresh"]:
            raise InvalidAccessToken()


class RefreshTokenBearer(TokenBearer):
    async def verify_token_data(
        self, token_data: dict, session: AsyncSession = Depends(get_session)
    ) -> None:
        if not token_data.get("refresh"):
            raise InvalidRefreshToken()

        if await is_token_revoked(token_data["jti"], session):
            raise InvalidRefreshToken()


async def get_current_user(
    token_details: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session),
):
    if token_details.get("refresh"):
        raise AccessTokenRequired()

    user_email = token_details["user"]["email"]
    user = await user_service.get_user(user_email, session)

    if not user:
        raise UserNotFound()
    return user
