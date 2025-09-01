from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.db.main import init_db
from src.auth.routes import auth_router
from .middleware import register_middleware


@asynccontextmanager
async def life_span(app: FastAPI):
    print("server is starting....")
    await init_db()
    yield
    print("server has been stopped")


version = "v1"
version_prefix = f"/api/{version}"

app = FastAPI(
    title="Ecommerce API",
    description="A REST API for E-Commerce with service",
    version=version,
    contact={"email": "cipherangelmadara@gmail.com"},
    openapi_url=f"{version_prefix}/openapi.json",
)

register_middleware(app)

app.include_router(auth_router, prefix=f"{version_prefix}/auth", tags=["auth"])


@app.get("/")
async def read_root():
    return {"message": "Hello world"}
