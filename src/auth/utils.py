from sqlmodel.ext.asyncio.session import AsyncSession
from passlib.context import CryptContext
from datetime import datetime, timedelta
from src.config import settings
from src.db.models import RefreshToken
import uuid
import jwt


password_context = CryptContext(schemes=["bcrypt"])

ACCESS_TOKEN_EXPIRY = 300
REFRESH_TOKEN_EXPIRY = 86400


def generate_password_hash(password: str) -> str:
    hash = password_context.hash(password)
    return hash


def verify_password(password: str, hash: str) -> bool:
    return password_context.verify(password, hash)


def create_access_token(
    user_data: dict, expiry: timedelta = None, refresh: bool = False
):
    payload = {}
    payload["user"] = user_data
    payload["exp"] = datetime.now() + (
        expiry if expiry is not None else timedelta(seconds=ACCESS_TOKEN_EXPIRY)
    )
    payload["jti"] = str(uuid.uuid4())
    payload["refresh"] = refresh
    token = jwt.encode(
        payload=payload, key=settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return token


async def create_refresh_token(
    user_data: dict, session: AsyncSession, expiry: timedelta = None
) -> str:
    expires = datetime.now() + (expiry if expiry is not None else timedelta(days=7))
    jti = str(uuid.uuid4())

    token_payload = {
        "user": user_data,
        "exp": expires.timestamp(),
        "jti": jti,
        "refresh": True,
    }

    token = jwt.encode(
        token_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )

    refresh_token = RefreshToken(
        jti=jti, user_uid=user_data["user_uid"], expires_at=expires, revoked=False
    )
    session.add(refresh_token)
    await session.commit()

    return token
