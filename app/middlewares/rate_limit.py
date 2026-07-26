import time
from collections import defaultdict

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window limiter, per client IP."""

    def __init__(self, app, calls: int = 100, period: int = 60) -> None:
        super().__init__(app)
        self.calls = calls
        self.period = period
        self._clients: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        self._clients[client_ip] = [
            t for t in self._clients[client_ip] if now - t < self.period
        ]

        if len(self._clients[client_ip]) >= self.calls:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Try again later."},
                headers={"Retry-After": str(self.period)},
            )
        self._clients[client_ip].append(now)
        return await call_next(request)
