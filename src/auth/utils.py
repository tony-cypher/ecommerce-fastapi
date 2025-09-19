from sqlmodel.ext.asyncio.session import AsyncSession
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jwt import ExpiredSignatureError
from src.config import settings
from src.db.models import RefreshToken
from src.errors import TokenExpired, InvalidToken
import uuid
import jwt
import logging
import hashlib


password_context = CryptContext(schemes=["bcrypt"])

ACCESS_TOKEN_EXPIRY = 180
REFRESH_TOKEN_EXPIRY = 86400


def generate_password_hash(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hash: str) -> bool:
    return password_context.verify(password, hash)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def create_access_token(
    user_data: dict, expiry: timedelta = None, refresh: bool = False
) -> str:
    """Generate a signed JWT access token"""
    expiry_time = datetime.now(timezone.utc) + (
        expiry if expiry is not None else timedelta(seconds=ACCESS_TOKEN_EXPIRY)
    )
    payload = {
        "user": user_data,
        "exp": int(expiry_time.timestamp()),
        "jti": str(uuid.uuid4()),
        "refresh": refresh,
    }
    return jwt.encode(
        payload=payload, key=settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )


async def create_refresh_token(
    user_data: dict, session: AsyncSession, expiry: timedelta = None
) -> str:
    """Generates and persists a refresh token in DB"""
    expires = datetime.now(timezone.utc) + (
        expiry if expiry is not None else timedelta(days=7)
    )
    jti = str(uuid.uuid4())

    token_payload = {
        "user": user_data,
        "exp": int(expires.timestamp()),
        "jti": jti,
        "refresh": True,
    }

    token = jwt.encode(
        token_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )

    # Save refresh token in DB
    refresh_token = RefreshToken(
        jti=jti, user_uid=user_data["user_uid"], expires_at=expires, revoked=False
    )
    session.add(refresh_token)
    await session.commit()

    return token


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token, raise error if invalid/expired"""
    try:
        return jwt.decode(
            jwt=token,
            key=settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": True},
        )

    except ExpiredSignatureError:
        logging.warning("Token has expired")

        raise TokenExpired()
    except jwt.PyJWTError as err:
        logging.exception("Invalid token: %s", err)
        raise InvalidToken()
