from fastapi import FastAPI

from app.api.routes import auth, offers, users

app = FastAPI(title="StageFlow", version="0.1.0")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(offers.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "StageFlow", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
