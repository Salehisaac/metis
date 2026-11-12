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
        # TODO: set record.request_id
        return True


log.addFilter(RequestIdFilter())
app = FastAPI()


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    # TODO: reuse a valid incoming X-Request-ID or generate one, remember it, return it as a header
    return await call_next(request)


# TODO: an exception handler for any unhandled Exception


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    if order_id == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    if order_id == 13:
        raise RuntimeError("payment gateway rejected key sk_live_51Hx")
    log.info("order fetched", extra={"order_id": order_id})
    return {"id": order_id}
