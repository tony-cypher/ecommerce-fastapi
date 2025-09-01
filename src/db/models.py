from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, Boolean
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime, timezone
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

    password_hash: str = Field(
        sa_column=Column(String(255), nullable=False), exclude=True
    )

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), default=utc_now, nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), default=utc_now, nullable=False)
    )

    def __repr__(self):
        return f"<User {self.username}"
