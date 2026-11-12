class Playlist(list):
    """Track ids in play order. A track may appear only once.

    Bug report: duplicates still get in. Only append() was overridden, and
    extend(), insert(), += and pl[i] = ... all bypass it.
    Refactor to composition; see exercise.json for the new interface.
    """

    def append(self, track: str) -> None:
        if track not in self:
            super().append(track)
