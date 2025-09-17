from fastapi_mail import ConnectionConfig
from src.config import settings


mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

# mail = FastMail(config=mail_config)


# def create_message(recipients: list[str], subject: str, body: str):
#     message = MessageSchema(
#         recipients=recipients, subject=subject, body=body, subtype=MessageType.html
#     )
#     return message
