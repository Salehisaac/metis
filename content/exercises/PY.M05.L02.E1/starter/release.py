from dataclasses import dataclass


# TODO: choose the right @dataclass options for Version (see the requirements).
@dataclass
class Version:
    """A semantic version like 1.10.2 (major.minor.patch)."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> "Version":
        raise NotImplementedError

    def __str__(self) -> str:
        raise NotImplementedError

    def next_minor(self) -> "Version":
        raise NotImplementedError


# TODO: Release has a version and a list of notes (empty by default).
@dataclass
class Release:
    version: Version
