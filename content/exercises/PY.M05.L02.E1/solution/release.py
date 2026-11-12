from dataclasses import dataclass, field, replace


@dataclass(frozen=True, order=True)
class Version:
    """A semantic version like 1.10.2 (major.minor.patch)."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> "Version":
        parts = text.strip().split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError(f"not a version: {text!r}")
        major, minor, patch = (int(p) for p in parts)
        return cls(major, minor, patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def next_minor(self) -> "Version":
        return replace(self, minor=self.minor + 1, patch=0)


@dataclass
class Release:
    version: Version
    notes: list[str] = field(default_factory=list)
