from pydantic import BaseModel, ConfigDict, ValidationError


class ImportedMessage(BaseModel):
    """One message row from a chat export."""

    model_config = ConfigDict(extra="forbid")

    id: int
    chat_id: int
    sender: str
    text: str
    reply_to: int | None = None
    tags: list[str] = []


def parse_rows(rows: list) -> tuple[list[ImportedMessage], list[dict]]:
    """Validate every row. Return (valid messages in input order, problems).

    Each problem is {"row": <index in rows>, "field": <loc joined with ".">, "type": <error type>}.
    """
    messages: list[ImportedMessage] = []
    problems: list[dict] = []
    for index, row in enumerate(rows):
        try:
            messages.append(ImportedMessage.model_validate(row))
        except ValidationError as exc:
            for err in exc.errors():
                field = ".".join(str(part) for part in err["loc"])
                problems.append({"row": index, "field": field, "type": err["type"]})
    return messages, problems
