from fastapi import APIRouter, Depends, status
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime
from src.db.main import get_session
from src.db.models import RefreshToken, User
from src.errors import InvalidRefreshToken, UserNotFound, UserAlreadyExists
from .service import UserService, PasswordResetService
from .schemas import (
    SignupModel,
    LoginModel,
    UserModel,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from .utils import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_url_safe_token,
)
from .dependencies import get_current_user, AccessTokenBearer, RefreshTokenBearer

auth_router = APIRouter()
user_service = UserService()
# password_reset_service = PasswordResetService(AsyncSession=Depends(get_session))


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user_data: SignupModel, session: AsyncSession = Depends(get_session)):
    email = user_data.email
    user_exists = await user_service.user_exists(email, session)

    if user_exists:
        raise UserAlreadyExists()

    new_user = await user_service.create_user(user_data, session)

    return {
        "message": "Account created successfully. Check email to verify your account",
        "user": new_user,
    }


@auth_router.get("/verify/{token}")
async def verify_user_account(token: str, session: AsyncSession = Depends(get_session)):
    token_data = decode_url_safe_token(token)
    email = token_data.get("email")

    if email:
        user = await user_service.get_user(email, session)

        if not user:
            raise UserNotFound()

        await user_service.update_user(user, {"is_verified": True}, session)

        return JSONResponse(
            content={"message": "Account verified successfully"},
            status_code=status.HTTP_200_OK,
        )


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


@auth_router.get("/refresh_token")
async def get_access_token(token_details: dict = Depends(RefreshTokenBearer())):
    expiry_time = token_details["exp"]

    if datetime.fromtimestamp(expiry_time) > datetime.now():
        access_token = create_access_token(user_data=token_details["user"])
        return JSONResponse(content={"access_token": access_token})

    raise InvalidRefreshToken()


@auth_router.post("/try-mail")
async def test_mail(
    data: ForgotPasswordRequest, session: AsyncSession = Depends(get_session)
):
    result = await session.exec(select(User).where(User.email == data.email))
    user = result.first()
    if not user:
        raise UserNotFound()

    service = PasswordResetService(session)
    await service.send_mail_test(user)
    return {"message": "Test Email sent"}


@auth_router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest, session: AsyncSession = Depends(get_session)
):
    result = await session.exec(select(User).where(User.email == data.email))
    user = result.first()
    if not user:
        raise UserNotFound()

    service = PasswordResetService(session)
    await service.send_reset_email(user)
    return {"message": "Password reset email sent"}


@auth_router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest, session: AsyncSession = Depends(get_session)
):
    service = PasswordResetService(session)
    await service.reset_password(token=data.token, new_password=data.new_password)
    return {"message": "Password has been reset successfully"}
