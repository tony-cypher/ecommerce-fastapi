import secrets
from fastapi_mail import FastMail, MessageSchema
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from datetime import datetime, timezone, timedelta
from src.db.models import User, PasswordResetToken
from src.mail import mail_config
from src.config import settings
from src.errors import InvalidToken, UserNotFound
from .schemas import SignupModel
from .utils import generate_password_hash


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
        new_user.password_hash = generate_password_hash(user_data["password"])
        new_user.role = "user"
        session.add(new_user)
        await session.commit()
        return new_user


class PasswordResetService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mail = FastMail(config=mail_config)

    async def send_mail_test(self, user: User):
        message = MessageSchema(
            subject="Test Mail",
            recipients=[user.email],
            body="<p>Testing on sending mails to emails </p>",
            subtype="html",
        )
        await self.mail.send_message(message)

    async def send_reset_email(self, user: User):
        # Generate secure token
        token = secrets.token_urlsafe(48)

        # Save reset token
        reset_token = PasswordResetToken(
            user_uid=user.uid,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        self.session.add(reset_token)
        await self.session.commit()
        await self.session.refresh(reset_token)

        # Email content
        reset_link = (
            f"http://{settings.DOMAIN}/api/v1/auth/reset-password?token={token}"
        )
        message = MessageSchema(
            subject="Password Reset Request",
            recipients=[user.email],
            body=f"<p>Click the link to reset your password: </p><a href='{reset_link}'>{reset_link}</a>",
            subtype="html",
        )

        await self.mail.send_message(message)

    async def reset_password(self, token: str, new_password: str):
        result = await self.session.exec(
            select(PasswordResetToken).where(PasswordResetToken.token == token)
        )
        reset_token = result.first()

        if not reset_token:
            raise InvalidToken()

        if reset_token.used or reset_token.expires_at < datetime.now(timezone.utc):
            raise InvalidToken()

        # Get user
        result = await self.session.exec(
            select(User).where(User.uid == reset_token.user_uid)
        )
        user = result.first()
        if not user:
            raise UserNotFound()

        # Update password
        user.password_hash = generate_password_hash(new_password)
        reset_token.used = True

        self.session.add(user)
        self.session.add(reset_token)
        await self.session.commit()
