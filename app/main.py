import logging

from fastapi import FastAPI

from app.api.routes import applications, auth, offers, stats, users
from app.middlewares.cors import configure_cors
from app.middlewares.rate_limit import RateLimitMiddleware
from app.middlewares.request_id import RequestIDMiddleware
from app.middlewares.security_headers import SecurityHeadersMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="StageFlow", version="0.1.0")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(offers.router)
app.include_router(applications.router)
app.include_router(stats.router)

app.add_middleware(SecurityHeadersMiddleware)
app = configure_cors(app)
# Generous limit on purpose: this protects against genuine abuse without
# tripping during an automated test run, which fires far more than a
# handful of requests per client "IP" in a few seconds.
app.add_middleware(RateLimitMiddleware, calls=1000, period=60)
app.add_middleware(RequestIDMiddleware)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "StageFlow", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
