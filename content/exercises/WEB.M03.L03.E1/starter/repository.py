# Finished: don't edit. In-memory storage until WEB.M05.
import itertools


class FolderRepository:
    def __init__(self):
        self._rows: dict[int, dict] = {}
        self._ids = itertools.count(1)

    def add(self, name: str) -> dict:
        row = {"id": next(self._ids), "name": name}
        self._rows[row["id"]] = row
        return row

    def get(self, folder_id: int) -> dict | None:
        return self._rows.get(folder_id)

    def all(self) -> list[dict]:
        return list(self._rows.values())

    def remove(self, folder_id: int) -> bool:
        return self._rows.pop(folder_id, None) is not None
