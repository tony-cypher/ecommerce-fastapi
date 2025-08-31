from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from src.db.models import User
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
