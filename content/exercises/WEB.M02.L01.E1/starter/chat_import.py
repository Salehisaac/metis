from pydantic import BaseModel, ConfigDict, ValidationError


class ImportedMessage(BaseModel):
    """One message row from a chat export. TODO: declare the fields (see exercise.json)."""


def parse_rows(rows: list) -> tuple[list[ImportedMessage], list[dict]]:
    """Validate every row. Return (valid messages in input order, problems).

    Each problem is {"row": <index in rows>, "field": <loc joined with ".">, "type": <error type>}.
    """
    raise NotImplementedError
