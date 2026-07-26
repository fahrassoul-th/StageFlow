import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("app.request")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request_id=%s method=%s path=%s status_code=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
        )
        return response
