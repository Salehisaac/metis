```python
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
```

**Why it works**

- **`frozen=True`** makes assignment to fields raise `FrozenInstanceError`. Because the generated `__eq__` and frozen go together, `@dataclass` also generates `__hash__`, so equal versions collapse in a set and can be dict keys.
- **`order=True`** generates `<`, `<=`, `>`, `>=` that compare the fields **as a tuple, in declaration order**: `(major, minor, patch)`. The fields are `int`s, so `1.10.0` beats `1.9.3`. Sorting the *strings* would put `"1.10.0"` before `"1.9.3"` (character `'1'` < `'9'`), which is the bug this type exists to prevent.
- **`parse` validates before converting.** `int()` alone is too lenient: `int("-2")` is `-2` and `int(" 2")` is `2`, so `"1.-2.3"` and `"1. 2.3"` would slip through. `str.isdigit()` is false for `""` (catches `"1..3"`), for `"-2"`, `" 2"` and `"v1"`. The length check catches `"1.2"` and `"1.2.3.4"`. Only `text.strip()` is applied, to the whole string, as the spec says.
- **`parse` is a classmethod** returning `cls(...)`, the alternate-constructor pattern from L01.
- **`__str__` vs `__repr__`:** `print` and `str()` use `__str__`; if a class doesn't define one, they fall back to `__repr__`. Defining only `__str__` keeps the generated, debug-friendly repr.
- **`next_minor`** can't modify `self` (it's frozen, and callers may share it), so it returns a new object. `replace` copies all fields and changes the ones you name; `Version(self.major, self.minor + 1, 0)` is equally fine.
- **`field(default_factory=list)`** calls `list()` for every new `Release`. A plain `= []` is refused by `@dataclass` with a ValueError, precisely because one list would be shared by all releases.

**Alternatives**

- `sorted(texts, key=lambda t: tuple(int(p) for p in t.split(".")))` (PY.M03) sorts strings correctly without a class, fine for a one-off script. The dataclass is better once versions are passed around and compared in several places.
- A regex like `\d+\.\d+\.\d+` with `re.fullmatch` is another valid way to validate.
