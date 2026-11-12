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
    email = email.strip().lower()
    capacity = repo.get_capacity(event_id)
    if capacity is None:
        raise EventNotFound(event_id)
    taken = repo.count_registrations(event_id)
    if taken >= capacity:
        raise EventFull(event_id)
    if not repo.add(event_id, email):
        raise AlreadyRegistered(email)
    return capacity - taken - 1
