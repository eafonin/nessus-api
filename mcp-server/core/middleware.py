"""Middleware for trace ID propagation and other cross-cutting concerns."""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware


class TraceMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and propagate trace IDs through requests.

    Generates UUID4 trace_id per HTTP request, stores in request.state,
    and adds X-Trace-Id response header.
    """

    async def dispatch(self, request, call_next):
        # Extract or generate trace ID
        trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
        request.state.trace_id = trace_id

        # Process request
        response = await call_next(request)

        # Add trace ID to response headers
        response.headers["X-Trace-Id"] = trace_id
        return response
