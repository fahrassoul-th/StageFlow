import logging

from fastapi import FastAPI

from app.api.routes import applications, auth, offers, stats, users
from app.middlewares.cors import configure_cors
from app.middlewares.rate_limit import RateLimitMiddleware
from app.middlewares.request_id import RequestIDMiddleware
from app.middlewares.security_headers import SecurityHeadersMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

openapi_tags = [
    {"name": "auth", "description": "Registration and JWT login (OAuth2 password flow)."},
    {"name": "users", "description": "The authenticated user's own profile."},
    {
        "name": "offers",
        "description": "Internship offers: draft -> submitted -> published/rejected.",
    },
    {
        "name": "applications",
        "description": "Student applications to a published offer: "
        "pending -> accepted/rejected/withdrawn.",
    },
    {"name": "stats", "description": "Aggregate counts for program managers."},
]

app = FastAPI(
    title="StageFlow",
    description=(
        "Internal API for a Master DSIA program to manage internship offers, "
        "student applications, and pedagogical review - with per-role visibility "
        "so each actor only sees and modifies what they're allowed to."
    ),
    version="0.1.0",
    openapi_tags=openapi_tags,
)

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
