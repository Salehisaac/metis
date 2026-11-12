"""Business rules only. No FastAPI imports, no SQL."""
from repository import RegistrationRepo


class RegistrationError(Exception):
    """Base class for rule violations."""


class EventNotFound(RegistrationError):
    pass


class EventFull(RegistrationError):
    pass


class AlreadyRegistered(RegistrationError):
    pass


def register(repo: RegistrationRepo, event_id: int, email: str) -> int:
    """Register email for the event and return the seats left afterwards.

    Emails are compared after strip() and lower(). Raises EventNotFound, EventFull or AlreadyRegistered.
    """
    raise NotImplementedError
