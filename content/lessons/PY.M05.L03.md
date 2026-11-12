---
{
  "id": "PY.M05.L03",
  "title": "Type hints; Protocol vs Go interfaces",
  "difficulty": "intermediate",
  "minutes": 50,
  "prerequisites": ["PY.M05.L02"],
  "objectives": [
    "Write type hints for parameters, returns and attributes, including list[...], dict[...] and X | None",
    "Demonstrate that Python doesn't enforce hints at runtime, and say who does read them",
    "Define a typing.Protocol for a dependency and satisfy it without inheritance, as with an implicit Go interface",
    "Predict what isinstance does with a @runtime_checkable protocol (method names only, not signatures)",
    "Define an ABC with @abstractmethod, predict when a missing method is reported, and choose Protocol or ABC for a given situation"
  ],
  "why": "Go's compiler checks your types and interfaces for you. Python's doesn't, which surprises Go developers twice: a wrong type sails through at runtime, and an 'interface' is just a convention unless you choose a tool to check it. Knowing what hints do and don't do is what lets you use FastAPI and Pydantic well later, and Protocol is how you write Go-style 'accept an interface' code that tests can fake.",
  "applications": [
    "Annotating service functions so IDEs and optional type checkers can catch mistakes",
    "Defining the small interface a function needs (a sender, a store, a clock) and passing fakes in tests",
    "Base classes that force subclasses to implement hooks (ABC)"
  ],
  "exercises": ["PY.M05.L03.E1"],
  "sources": [
    {
      "title": "typing: Support for type hints",
      "url": "https://docs.python.org/3.12/library/typing.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "The Python runtime does not enforce function and variable type annotations; type checkers, IDEs and linters use them",
        "Protocol classes support structural subtyping (static duck typing): a class with matching methods needs no explicit base class",
        "runtime_checkable isinstance checks only the presence of the required methods or attributes, not their signatures or types",
        "X | None is equivalent to Optional[X]; int | str is the recommended union shorthand",
        "list[int] is the generic form of list",
        "The typing docs point to the mypy documentation for further reading"
      ]
    },
    {
      "title": "abc: Abstract Base Classes",
      "url": "https://docs.python.org/3.12/library/abc.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "ABC is a helper class with ABCMeta as its metaclass",
        "A class with abstract methods cannot be instantiated unless all abstract methods are overridden",
        "register() makes a virtual subclass recognised by isinstance and issubclass"
      ]
    },
    {
      "title": "Glossary: type hint, annotation, duck-typing, abstract base class",
      "url": "https://docs.python.org/3.12/glossary.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "Type hints are optional and not enforced by Python, but useful to static type checkers and IDEs",
        "Annotations of functions are stored in __annotations__",
        "Duck typing uses an object's methods without checking its type",
        "ABCs complement duck typing as a way to define interfaces"
      ]
    }
  ]
}
---
## 1. Writing hints: the Go types you know

A type hint is an annotation after a name: `name: type` for parameters and variables, `-> type` for the return value. You've been reading them since PY.M01. The common ones, next to Go:

| Go | Python hint |
|---|---|
| `int`, `string`, `bool`, `float64` | `int`, `str`, `bool`, `float` |
| `[]string` | `list[str]` |
| `map[string]int` | `dict[str, int]` |
| `*User` that may be `nil` | `User \| None` |
| a fixed pair `(int, string)` | `tuple[int, str]` |
| `func(int) string` | `Callable[[int], str]` (from `collections.abc`) |
| `any` | `object`, or `Any` from `typing` |

```python
def find_user(users: dict[int, User], user_id: int) -> User | None:
    return users.get(user_id)
```

`User | None` is the Python way of saying "may return nothing". Callers must check `if user is None:` before using it, just like a nil check in Go. (Older code writes `Optional[User]`; it means exactly the same thing.)

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "`last_message(chat_id)` returns the newest message text, or nothing when the chat is empty. Which return hint fits?",
  "options": [
    "`-> None`",
    "`-> list[str]`",
    "`-> str | None`",
    "`-> str`"
  ], "answer": 2,
  "explanation": "str | None says 'a string, or None when there is none', like a nil-able pointer in Go. -> None would mean it never returns a value." }
```

## 2. Python doesn't check them

This is the big difference from Go. In Go a wrong type doesn't compile. In Python **hints are not enforced at runtime at all**; they're stored, and nothing else happens:

```python
def unread_badge(count: int) -> str:
    return f"{count} new"


print(unread_badge(3))
print(unread_badge("lots"))
print(unread_badge(None))
print(unread_badge.__annotations__)
```

```text
3 new
lots new
None new
{'count': <class 'int'>, 'return': <class 'str'>}
```

No error, no warning. The function stores its hints in `__annotations__` and runs its body whatever you pass. The return hint isn't checked either: a function annotated `-> int` can return a string.

The flip side of the same rule: **any object that has what the code uses works**, whatever its declared type. `sum(len(n) for n in names)` inside a function annotated `names: list[str]` works just as well with a tuple or a dict. That's duck typing ("if it quacks like a duck..."), and it's the reason Python had interfaces without the word.

**Common mistake:** treating a hint as validation. `def set_limit(n: int)` called with `"60"` from a query string keeps the string. At a trust boundary, convert and check yourself (`int(value)`, which raises ValueError), or let a validating library do it (Pydantic, WEB.M02).

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "def double(n: int) -> int:\n    return n * 2\n\nprint(double(\"ab\"), double([0]))",
  "answer": "abab [0, 0]",
  "explanation": "The hints aren't checked. \"ab\" * 2 is \"abab\" and [0] * 2 is [0, 0], because * works on strings and lists too." }
```

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "If a function is annotated `-> int` and returns a string, Python raises a TypeError when it returns.", "answer": false,
  "explanation": "Return hints are ignored at runtime just like parameter hints. Only a separate type checker or a validating library would notice." }
```

## 3. So who reads hints?

- **You and your team.** A signature with hints is documentation that can't drift as easily as a comment.
- **Your editor.** It uses hints for completion and red underlines.
- **Static type checkers** read the code without running it and report mismatches, much like `go vet` plus the compiler's type check. *mypy* is the best-known one, and the official typing docs point to its documentation. It's **optional and not installed in this academy**; nothing here requires it.
- **Libraries that choose to use them.** `@dataclass` reads annotations to find the fields (L02), but not to check values. Some libraries go further and use hints to validate data; you'll meet that with Pydantic in WEB.M02. Whatever they do is the library's feature, not Python's.

So in this academy your safety net is the same as everywhere else: **tests**. Hints help you and your tools read the code; tests prove that it works.

## 4. Go interfaces → `typing.Protocol`

A Go interface is satisfied implicitly: any type with the right methods is a `Sender`, and nobody writes `implements`. Python's `typing.Protocol` is the same idea, **structural typing**, written as a class whose methods have only `...` as a body:

```python
from typing import Protocol


class Sender(Protocol):
    def send(self, chat_id: int, text: str) -> None: ...


class TelegramSender:
    def send(self, chat_id: int, text: str) -> None:
        print(f"-> chat {chat_id}: {text}")


class RecordingSender:
    """Test fake: remembers what was sent instead of sending it."""

    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    def send(self, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))


def notify_mentions(sender: Sender, chat_id: int, names: list[str]) -> int:
    for name in names:
        sender.send(chat_id, f"@{name} you were mentioned")
    return len(names)


notify_mentions(TelegramSender(), 7, ["ali"])
fake = RecordingSender()
print(notify_mentions(fake, 7, ["ali", "sara"]), fake.sent)
```

```text
-> chat 7: @ali you were mentioned
2 [(7, '@ali you were mentioned'), (7, '@sara you were mentioned')]
```

Neither sender inherits from `Sender` or mentions it. `notify_mentions` depends only on "something with `send(chat_id, text)`", so production passes the real sender and the test passes a fake that records calls. That's the Go habit of keeping an interface small and defining it where it's used, in Python.

The difference from Go: **at runtime, `Sender` changes nothing.** Python would run `notify_mentions(42, 7, ["ali"])` until it hit `42.send` and raised AttributeError. The protocol is checked only by a type checker (or by your tests). It's documentation that tools can verify.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "You pass an object with no `send` method to `notify_mentions(sender: Sender, ...)` and run it (no type checker). What happens?",
  "options": [
    "TypeError at the call, because the argument doesn't match the Sender protocol",
    "AttributeError at sender.send, and only if names isn't empty",
    "Nothing happens, because Protocol methods have default empty bodies",
    "An error when the module is imported, before anything is called"
  ], "answer": 1,
  "explanation": "Annotations aren't checked at runtime, so the call goes ahead. The failure comes only when sender.send is looked up, so with an empty names list nothing fails at all. That's one more reason to test the empty case." }
```

## 5. `@runtime_checkable`: isinstance that only counts names

If you mark a protocol `@runtime_checkable`, you may use it with `isinstance`. But the check only looks for **attributes with the right names**; it doesn't compare parameters or types:

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class Sender(Protocol):
    def send(self, chat_id: int, text: str) -> None: ...


class EmailSender:
    def send(self) -> None:          # wrong signature
        pass


class Logger:
    def log(self, text: str) -> None:
        pass


print(isinstance(EmailSender(), Sender), isinstance(Logger(), Sender))
```

```text
True False
```

`EmailSender` passes even though calling `send(7, "hi")` on it would raise TypeError. Use it as a cheap sanity check, not as a contract check.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Protocol, runtime_checkable\n\n@runtime_checkable\nclass Store(Protocol):\n    def save(self, text: str) -> int: ...\n    def count(self) -> int: ...\n\nclass A:\n    def save(self): ...\n    def count(self): ...\n\nclass B:\n    def save(self, text: str) -> int:\n        return 1\n\nprint(isinstance(A(), Store), isinstance(B(), Store))",
  "answer": "True False",
  "explanation": "A has both names, so it passes even with the wrong signatures. B is missing count, so it fails, however correct its save is." }
```

## 6. ABCs: interfaces you must inherit

Python also has the Java-style approach: an **abstract base class** (ABC). Subclasses must inherit from it explicitly (**nominal** typing), and Python does enforce one thing at runtime: you can't create an instance of a class that still has abstract methods.

```python
from abc import ABC, abstractmethod


class MessageStore(ABC):
    @abstractmethod
    def save(self, chat_id: int, text: str) -> int: ...

    @abstractmethod
    def last(self, chat_id: int, n: int) -> list[str]: ...

    def last_one(self, chat_id: int) -> str | None:
        msgs = self.last(chat_id, 1)
        return msgs[0] if msgs else None


class HalfStore(MessageStore):
    def save(self, chat_id: int, text: str) -> int:
        return 1


try:
    HalfStore()
except TypeError as e:
    print("TypeError:", e)


class DuckStore:
    def save(self, chat_id: int, text: str) -> int:
        return 1

    def last(self, chat_id: int, n: int) -> list[str]:
        return []


print(isinstance(DuckStore(), MessageStore))
```

```text
TypeError: Can't instantiate abstract class HalfStore without an implementation for abstract method 'last'
False
```

Three things to notice:

- The error comes when you **create** a `HalfStore`, not when the class is defined, and not when the missing method is called. That's earlier than duck typing, but still at runtime, not compile time.
- `DuckStore` has every method but **isn't** a `MessageStore`, because it doesn't inherit. Nominal typing ignores shape. (`MessageStore.register(DuckStore)` can declare it a "virtual subclass", but that's rarely what you want.)
- An ABC can carry **shared code**: `last_one` is a normal method built on the abstract `last`. A Go interface can't hold code; you'd write a helper function instead.

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "`class PgStore(MessageStore)` implements `save` but forgets `last`, where MessageStore is the ABC above. When is the mistake reported?",
  "options": [
    "When `PgStore()` is called: TypeError",
    "When the class statement runs, at import time",
    "Only when someone calls `store.last(...)` on it",
    "Never, unless a separate type checker is run"
  ], "answer": 0,
  "explanation": "ABCs check at instantiation: an object can't be created while any abstract method is unimplemented. With a Protocol nothing is checked at runtime; the error would come at the call to the missing method." }
```

## 7. Choosing: Protocol or ABC?

| | `Protocol` | `ABC` |
|---|---|---|
| Typing style | structural, like Go interfaces | nominal: must inherit |
| Runtime check | none (optional `isinstance` by names only) | can't instantiate with missing methods |
| Shared code | not meant for it | yes, concrete methods |
| Where it's defined | next to the code that **uses** it | next to the base implementation |
| Typical use | dependencies you want to fake: sender, store, clock | a framework's base class with required hooks |

**Default to Protocol** when you're describing what a function needs from its dependency. It's the Go habit you already have, and fakes don't need to import or inherit anything. **Reach for an ABC** when you own a base class that has real shared logic and want a missing hook reported as soon as someone instantiates the subclass. And often you need neither: plain duck typing plus a test covers small internal code.

```quiz
{ "id": "q7", "type": "choice", "label": "Application",
  "prompt": "Your `PushNotifier` service calls an external push API through a client object with one method, `push(device_token, payload)`. In tests you want a fake client that records calls. What fits best?",
  "options": [
    "An ABC with `push` that the third-party client library must inherit from",
    "No hints at all: annotate the parameter as `object` and document it",
    "A `Protocol` with `push`, defined next to PushNotifier",
    "Subclass the real client in tests and override `push` there"
  ], "answer": 2,
  "explanation": "You can't make a third-party class inherit your ABC, and a Protocol needs no inheritance: the real client fits if it has push, and so does a recording fake. object hides the contract from readers and tools. Subclassing the real client drags in its constructor and network setup." }
```

## 8. Your turn

The exercise is the clock version of section 4: a limiter that reads the real time directly can't be tested without sleeping. You'll write a fake that satisfies a given protocol structurally and inject it.

```exercise
PY.M05.L03.E1
```
