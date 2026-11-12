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
