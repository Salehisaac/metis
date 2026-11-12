"""API with request IDs and an error handler that reports failures without leaking details."""
import logging
import re
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

VALID_ID = re.compile(r"^[A-Za-z0-9-]{1,64}$")
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
log = logging.getLogger("app")


class RequestIdFilter(logging.Filter):
    """Copies the current request ID onto every record logged through `log`."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


log.addFilter(RequestIdFilter())
app = FastAPI()


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    incoming = request.headers.get("X-Request-ID", "")
    rid = incoming if VALID_ID.match(incoming) else uuid.uuid4().hex
    request_id_var.set(rid)
    resp = await call_next(request)
    resp.headers["X-Request-ID"] = rid
    return resp


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    rid = request_id_var.get()
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "request_id": rid},
        headers={"X-Request-ID": rid},
    )


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    if order_id == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    if order_id == 13:
        raise RuntimeError("payment gateway rejected key sk_live_51Hx")
    log.info("order fetched", extra={"order_id": order_id})
    return {"id": order_id}
