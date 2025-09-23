import secrets

import httpx
from fastapi import HTTPException, status
from fastapi_mail import FastMail, MessageSchema

# from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, delete
from datetime import datetime, timezone, timedelta

from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from src.db.models import User, PasswordResetToken
from src.mail import mail_config
from src.config import settings
from src.errors import InvalidToken, UserNotFound, FailedOauth
from .schemas import SignupModel
from .utils import (
    generate_password_hash,
    hash_token,
    create_url_safe_token,
    verify_password,
    create_access_token,
    create_refresh_token,
)


async def generate_tokens(user: dict, session: AsyncSession):
    access_token = create_access_token(
        user_data={
            "email": user.email,
            "user_uid": str(user.uid),
            "role": user.role,
        }
    )
    refresh_token = await create_refresh_token(
        user_data={"email": user.email, "user_uid": str(user.uid)},
        session=session,
    )

    return {"access_token": access_token, "refresh_token": refresh_token}


class UserService:
    async def get_user(self, email: str, session: AsyncSession):
        statement = select(User).where(User.email == email)
        result = await session.exec(statement)
        user = result.first()
        return user

    async def user_exists(self, email, session: AsyncSession):
        user = await self.get_user(email, session)
        return True if user is not None else False

    async def create_user(self, data: SignupModel, session: AsyncSession):
        user_data = data.model_dump()
        new_user = User(**user_data)
        email = user_data["email"]
        new_user.password_hash = generate_password_hash(user_data["password"])
        new_user.role = "user"
        session.add(new_user)
        await session.commit()

        token = create_url_safe_token({"email": email})
        link = f"http://{settings.DOMAIN}/api/v1/auth/verify/{token}"
        mail = FastMail(config=mail_config)
        message = MessageSchema(
            subject="Verify your Email",
            recipients=[email],
            body=f"<p>Click the <a href='{link}'>link</a> to verify your email/p>",
            subtype="html",
        )

        await mail.send_message(message)

        return new_user

    async def login(self, data: dict, session: AsyncSession):
        email = data.email
        password = data.password

        user = await self.get_user(email, session)

        if user is not None:
            password_valid = verify_password(password, user.password_hash)

            if password_valid:
                tokens = await generate_tokens(user, session)

                return {
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "user": {"email": user.email, "uid": str(user.uid)},
                }

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Email or Password"
        )

    async def update_user(self, user: User, user_data: dict, session: AsyncSession):
        for k, v in user_data.items():
            setattr(user, k, v)

        await session.commit()
        return user


class PasswordResetService:
    def __init__(self):
        self.mail = FastMail(config=mail_config)

    async def send_mail_test(self, user: User):
        message = MessageSchema(
            subject="Test Mail",
            recipients=[user.email],
            body="<p>Testing on sending mails to emails </p>",
            subtype="html",
        )
        await self.mail.send_message(message)

    async def send_reset_email(self, user: User, session: AsyncSession):
        # Delete all old tokens for this user
        await session.exec(
            delete(PasswordResetToken).where(PasswordResetToken.user_uid == user.uid)
        )

        # Generate secure token
        raw_token = secrets.token_urlsafe(48)
        token_hash = hash_token(raw_token)

        # Save hashed reset token
        reset_token = PasswordResetToken(
            user_uid=user.uid,
            token=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        self.session.add(reset_token)
        await self.session.commit()
        await self.session.refresh(reset_token)

        # Email content
        reset_link = (
            f"http://{settings.DOMAIN}/api/v1/auth/reset-password?token={raw_token}"
        )
        message = MessageSchema(
            subject="Password Reset Request",
            recipients=[user.email],
            body=f"<p>Click the link to reset your password: </p><a href='{reset_link}'>{reset_link}</a>",
            subtype="html",
        )

        await self.mail.send_message(message)

    async def reset_password(
        self, token: str, new_password: str, session: AsyncSession
    ):
        token_hash = hash_token(token)

        result = await session.exec(
            select(PasswordResetToken).where(PasswordResetToken.token == token_hash)
        )
        reset_token = result.first()

        if not reset_token:
            raise InvalidToken()

        if reset_token.used or reset_token.expires_at < datetime.now(timezone.utc):
            raise InvalidToken()

        # Fetch user
        result = await session.exec(
            select(User).where(User.uid == reset_token.user_uid)
        )
        user = result.first()
        if not user:
            raise UserNotFound()

        # Update password
        user.password_hash = generate_password_hash(new_password)
        reset_token.used = True

        session.add(user)
        session.add(reset_token)
        await session.commit()


class GoogleAuthService:
    def __init__(self):
        self.redirect_url = f"http://{settings.DOMAIN}/api/v1/auth/oauth2callback"

    async def google_login(self):
        google_oauth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={settings.CLIENT_ID}"
            f"&redirect_uri={self.redirect_url}"
            "&response_type=code"
            "&scope=openid%20email%20profile"
        )
        return {"auth_url": google_oauth_url}

    async def google_callback(self, code: str, session: AsyncSession):
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.CLIENT_ID,
            "client_secret": settings.CLIENT_SECRET,
            "redirect_uri": self.redirect_url,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            token_data = response.json()

        if "id_token" not in token_data:
            raise FailedOauth()

        idinfo = id_token.verify_oauth2_token(
            token_data["id_token"], grequests.Request(), settings.CLIENT_ID
        )

        google_id = idinfo["sub"]
        email = idinfo.get("email")
        first_name = idinfo.get("given_name")
        last_name = idinfo.get("family_name")

        result = await session.exec(select(User).where(User.email == email))
        user = result.first()

        if not user:
            user = User(
                username=email.split("@")[0],
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_verified=True,
                auth_provider="google",
                google_id=google_id,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        tokens = await generate_tokens(user, session)
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": {
                "uid": user.uid,
                "email": user.email,
                "auth_provider": user.auth_provider,
            },
        }
