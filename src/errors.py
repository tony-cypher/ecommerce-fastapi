from fastapi import HTTPException, status


class EcommerceException(HTTPException):
    """This is the base class for all E-commerce errors"""

    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        message: str = "An unexpected error occurred",
        resolution: str = "Contact support",
        error_code: str = "UnknownError",
    ):
        detail = {
            "message": message,
            "resolution": resolution,
            "error_code": error_code,
        }
        super().__init__(status_code=status_code, detail=detail)


class InvalidToken(EcommerceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Token is invalid or expired",
            resolution="Please provide a new token",
            error_code="InvalidToken",
        )


class InvalidAccessToken(EcommerceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Access token is invalid or expired",
            resolution="Please provide a new access token",
            error_code="InvalidAccessToken",
        )


class InvalidRefreshToken(EcommerceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Refresh token is invalid or expired",
            resolution="Please provide a valid refresh token",
            error_code="InvalidRefreshToken",
        )


class TokenExpired(EcommerceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Token has expired",
            resolution="Please login again",
            error_code="TokenExpired",
        )


class AccessTokenRequired(EcommerceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Refresh token cannot be used for authentication",
            resolution="Provide a valid access token",
            error_code="AccessTokenRequired",
        )


class UserNotFound(EcommerceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found",
            resolution="Ensure the user exists or register a new account",
            error_code="UserNotFound",
        )


class UserAlreadyExists(EcommerceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message="User with email already exists",
            resolution="User already exists, try login",
            error_code="UserAlreadyExists",
        )


class InvalidCredentials(EcommerceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Invalid Credentials",
            resolution="Check details and try again",
            error_code="InvalidCredentials",
        )


class FailedOauth(EcommerceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Failed to obtain ID token",
            resolution="Try again",
            error_code="FailedIDToken",
        )
