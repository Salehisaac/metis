```python
class ImportedMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    chat_id: int
    sender: str
    text: str
    reply_to: int | None = None
    tags: list[str] = []


def parse_rows(rows: list) -> tuple[list[ImportedMessage], list[dict]]:
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
```

**Why it works**

- **The model is the whole rule set.** Four required fields have no default; `reply_to` is optional *and* nullable (`int | None = None`); `tags` defaults to an empty list, copied per instance. `extra="forbid"` turns `is_admin` into an `extra_forbidden` error instead of silently dropping it.
- **`model_validate`, not `ImportedMessage(**row)`.** A row like `"garbage"` or `None` can't be unpacked with `**`; that would raise `TypeError` and crash the import. `model_validate` reports it as a normal `model_type` error with an empty `loc`, so `".".join(...)` gives `""`.
- **`str(part)` in the join.** `loc` can contain ints: the second item of `tags` is `('tags', 1)`. Joining without `str()` raises `TypeError`.
- **`try` around one row at a time.** One bad row doesn't stop the rest, and `enumerate` keeps the row numbers aligned with the input, which is what a person fixing the file needs.
- **Report `type`, not `msg`.** The type codes are stable and testable; the messages are English text that can change between Pydantic versions.

**Alternatives**

- `pydantic.TypeAdapter(list[ImportedMessage]).validate_python(rows)` validates the whole list in one call, with locs like `(1, 'chat_id')`. But it's all or nothing: one bad row and you get no valid messages back.
- For huge exports you'd stream rows (a generator from PY.M07) instead of building both lists in memory.
