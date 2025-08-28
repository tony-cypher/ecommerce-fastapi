from fastapi import FastAPI

version = "v1"
version_prefix = f"/api/{version}"

app = FastAPI(
    title="Ecommerce API",
    description="A REST API for E-Commerce with service",
    version=version,
    contact={"email": "cipherangelmadara@gmail.com"},
    openapi_url=f"{version_prefix}/openapi.json",
)


@app.get("/")
async def read_root():
    return {"message": "Hello world"}
