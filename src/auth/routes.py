from fastapi import APIRouter, Depends, status
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session
from src.db.models import RefreshToken
from .service import UserService
from .schemas import SignupModel, LoginModel, UserModel
from .utils import verify_password, create_access_token, create_refresh_token
from .dependencies import get_current_user, AccessTokenBearer

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


@auth_router.post("/login")
async def login(data: LoginModel, session: AsyncSession = Depends(get_session)):
    email = data.email
    password = data.password

    user = await user_service.get_user(email, session)

    if user is not None:
        password_valid = verify_password(password, user.password_hash)

        if password_valid:
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

            return JSONResponse(
                content={
                    "message": "Login successful",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {"email": user.email, "uid": str(user.uid)},
                }
            )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Email or Password"
    )


@auth_router.get("/me", response_model=UserModel)
async def current_user(user=Depends(get_current_user)):
    return user


@auth_router.get("/logout")
async def logout(
    token_details: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session),
):
    user_uid = token_details["user"]["user_uid"]

    result = await session.exec(
        select(RefreshToken).where(
            RefreshToken.user_uid == user_uid, RefreshToken.revoked.is_(False)
        )
    )

    tokens = result.all()

    for token in tokens:
        token.revoked = True
        session.add(token)

    await session.commit()

    return JSONResponse(
        content={"message": "Logged out successfully"}, status_code=status.HTTP_200_OK
    )
