from fastapi import APIRouter, Depends, status
from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session
from .service import UserService
from .schemas import SignupModel, LoginModel
from .utils import verify_password

auth_router = APIRouter()
user_service = UserService()


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user_data: SignupModel, session: AsyncSession = Depends(get_session)):
    email = user_data.email
    user_exists = await user_service.user_exists(email, session)

    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User with email already exists",
        )
    new_user = await user_service.create_user(user_data, session)
    return {"message": "Account created successfully", "user": new_user}


@auth_router.post("login")
async def login(data: LoginModel, session: AsyncSession = Depends(get_session)):
    email = data.email
    password = data.password

    user = await user_service.get_user(email, session)

    if user is not None:
        password_valid = verify_password(password, user.password_hash)

        if password_valid:
            pass
