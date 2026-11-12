```python
from collections.abc import Iterable, Iterator


class Playlist:
    """Track ids in play order. A track may appear only once."""

    def __init__(self) -> None:
        self._tracks: list[str] = []

    def add(self, track: str) -> bool:
        if track in self._tracks:
            return False
        self._tracks.append(track)
        return True

    def add_many(self, tracks: Iterable[str]) -> int:
        return sum(self.add(t) for t in tracks)

    def remove(self, track: str) -> bool:
        if track not in self._tracks:
            return False
        self._tracks.remove(track)
        return True

    @property
    def tracks(self) -> tuple[str, ...]:
        return tuple(self._tracks)

    def __len__(self) -> int:
        return len(self._tracks)

    def __iter__(self) -> Iterator[str]:
        return iter(self._tracks)

    def __contains__(self, track: object) -> bool:
        return track in self._tracks
```

**Why it works**

- **Composition shrinks the surface.** A `list` subclass inherits all of list's methods (11 public ones, plus dunders), and every one that adds or replaces items (`extend`, `insert`, `__iadd__`, `__setitem__`, slice assignment) skips your `append` override, because the built-in list's methods don't call `append` internally. Wrapping a list means Playlist has only the methods you wrote, so there is no back door.
- **One place for the rule.** `add` is the only code that checks for duplicates; `add_many` calls it for every track. Duplicates inside the input (`["b", "b"]`) are handled for free, because the second `add` sees the first. `sum(...)` works because `True` counts as `1`.
- **No aliasing leaks.** `tracks` returns `tuple(self._tracks)`, a new immutable snapshot. Returning `self._tracks` itself would let callers `append` duplicates straight into your internal list (PY.M02).
- **Dunder methods give back the list-like feel.** `__len__` makes `len(p)` work, `__iter__` makes `for` and `list(p)` work, and `__contains__` makes `in` fast and explicit. (Without `__contains__`, `in` would still work by iterating, through `__iter__`.)
- **Explicit delegation is the price.** Go embedding would promote the inner methods automatically; Python makes you write each one. Here that's the point: you choose what to expose.

**Alternatives and limits**

- `track in self._tracks` scans the list, which is O(n). For long playlists keep a `set` next to the list, or use a `dict` as an ordered set (`self._tracks: dict[str, None] = {}`; dicts keep insertion order), which makes `add` and `in` O(1).
- `collections.UserList` doesn't help here: its `extend` doesn't call `append` either (checked on 3.12.3), so you'd still have to override every adding method. Composition is less code and harder to break.
