from fastapi import FastAPI

app = FastAPI(title="StageFlow", version="0.1.0")


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "StageFlow", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
