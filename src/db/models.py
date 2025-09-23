from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Boolean, ForeignKey
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import uuid


def utc_now():
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
        )
    )

    username: str = Field(sa_column=Column(String(50), unique=True, nullable=False))
    email: str = Field(sa_column=Column(String(255), unique=True, nullable=False))
    first_name: str = Field(sa_column=Column(String(100), nullable=False))
    last_name: str = Field(sa_column=Column(String(100), nullable=False))

    role: str = Field(
        sa_column=Column(pg.VARCHAR(20), nullable=False, server_default="user")
    )
    is_verified: bool = Field(
        sa_column=Column(Boolean, nullable=False, server_default="false")
    )

    password_hash: Optional[str] = Field(default=None, exclude=True)

    auth_provider: str = Field(
        sa_column=Column(pg.VARCHAR(50), nullable=False, server_default="local")
    )
    google_id: Optional[str] = Field(
        sa_column=Column(pg.VARCHAR(255), unique=True, nullable=True)
    )

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), default=utc_now, nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), default=utc_now, nullable=False)
    )
    refresh_tokens: List["RefreshToken"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"},
    )

    def __repr__(self):
        return f"<User {self.username}"


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: uuid.UUID = Field(
        sa_column=Column(pg.UUID, primary_key=True, default=uuid.uuid4, nullable=False)
    )
    jti: str = Field(
        sa_column=Column(pg.VARCHAR, index=True, nullable=False, unique=True)
    )
    user_uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, ForeignKey("users.uid", ondelete="CASCADE"), nullable=False
        )
    )
    expires_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), default=utc_now, nullable=False)
    )
    revoked: bool = Field(default=False)
    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), default=utc_now, nullable=False)
    )
    user: Optional[User] = Relationship(back_populates="refresh_tokens")


class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_reset_tokens"

    id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    )
    user_uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("users.uid", ondelete="CASCADE"),
            nullable=False,
        )
    )
    token: str = Field(sa_column=Column(pg.VARCHAR(255), unique=True, nullable=False))
    expires_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            default=lambda: utc_now() + timedelta(minutes=30),
        ),
    )
    used: bool = Field(
        sa_column=Column(Boolean, nullable=False, server_default="false")
    )
    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), default=utc_now, nullable=False)
    )
