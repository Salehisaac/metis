---
{
  "id": "PY.M05.L02",
  "title": "dataclasses",
  "difficulty": "beginner",
  "minutes": 45,
  "prerequisites": ["PY.M05.L01", "PY.M02.L04"],
  "objectives": [
    "Declare a domain type with @dataclass and predict its generated __init__, __repr__ and ==",
    "Give a list or dict field a safe default with field(default_factory=...) and explain why = [] is refused",
    "Use frozen=True for value objects, explain why frozen is shallow, and change values with dataclasses.replace",
    "Predict hashability: frozen dataclasses hash, normal ones raise TypeError in a set or as a dict key",
    "Use order=True, field(compare=False / repr=False) and __post_init__ for sorting, secrets and validation"
  ],
  "why": "A dataclass is the closest thing Python has to a Go struct: a declared list of typed fields with sane printing and field-by-field ==. Most domain models, DTOs and test data you'll write are dataclasses (or, at the HTTP boundary, Pydantic models in WEB.M02, which look very similar).",
  "applications": [
    "Domain models: User, Chat, Message with declared fields",
    "Value objects used as dict keys or set members (ids, references, versions)",
    "Readable test failures: pytest shows the generated repr of both sides"
  ],
  "exercises": ["PY.M05.L02.E1"],
  "sources": [
    {
      "title": "dataclasses: Data Classes",
      "url": "https://docs.python.org/3.12/library/dataclasses.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "@dataclass generates __init__, __repr__ and __eq__ by default; __eq__ compares as a tuple of fields in order",
        "order=True generates <, <=, >, >= comparing fields as a tuple in order",
        "frozen=True makes field assignment raise FrozenInstanceError",
        "eq and frozen both true generate __hash__; eq true and frozen false set __hash__ to None (unhashable)",
        "Unhashable defaults such as list raise ValueError; use field(default_factory=list)",
        "A field without a default after a field with a default raises TypeError",
        "field(repr=False) and field(compare=False) exclude a field from repr / comparisons",
        "__post_init__ is called by the generated __init__",
        "replace() creates a new object with some fields changed; asdict() converts to a dict",
        "Apart from ClassVar and InitVar, nothing in @dataclass examines the annotated type"
      ]
    }
  ]
}
---
## 1. A struct, for real this time

L01 ended with two complaints about plain classes: you write every attribute three times (`name: str`, `name`, `self.name = name`), and you get no useful printing or `==`. `@dataclass` fixes both. You **declare the fields once**, with type annotations, and it generates the methods:

```python
from dataclasses import dataclass


@dataclass
class User:
    user_id: int
    name: str
    is_bot: bool = False


ali = User(1, "ali")
print(ali)
print(ali == User(1, "ali"), ali == User(1, "ali", is_bot=True))
ali.name = "Ali"
print(ali)
```

```text
User(user_id=1, name='ali', is_bot=False)
True False
User(user_id=1, name='Ali', is_bot=False)
```

What `@dataclass` generated, compared with Go:

| Generated | What it does | Go equivalent |
|---|---|---|
| `__init__(self, user_id, name, is_bot=False)` | parameters in field order, defaults included | `User{ID: 1, Name: "ali"}` |
| `__repr__` | `User(user_id=1, name='ali', is_bot=False)` | `fmt.Printf("%+v", u)` |
| `__eq__` | same class and all fields equal, compared like a tuple | `u1 == u2` on comparable structs |

It's still an ordinary class: you can add methods, properties and classmethods exactly as in L01, and instances still have reference semantics (assigning or passing one never copies it). A dataclass is mutable by default: `ali.name = "Ali"` just works.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "from dataclasses import dataclass\n\n@dataclass\nclass Reaction:\n    emoji: str\n    user_id: int\n\na = Reaction(\"+1\", 7)\nb = Reaction(\"+1\", 7)\nprint(a == b, a is b)\nprint(Reaction(user_id=3, emoji=\"fire\"))",
  "answer": "True False\nReaction(emoji='fire', user_id=3)",
  "explanation": "The generated __eq__ compares fields, so a == b, but they are still two objects (a is b is False). The repr lists fields in declaration order, whatever order you passed the keyword arguments in." }
```

## 2. Defaults: ordering, and the mutable-default trap again

Two rules for defaults, both enforced when the **class is defined** (not later, when you use it):

```python
from dataclasses import dataclass
try:
    @dataclass
    class Chat:
        title: str
        member_ids: list[int] = []
except ValueError as e:
    print("ValueError:", e)
try:
    @dataclass
    class Message:
        text: str = ""
        chat_id: int
except TypeError as e:
    print("TypeError:", e)
```

```text
ValueError: mutable default <class 'list'> for field member_ids is not allowed: use default_factory
TypeError: non-default argument 'chat_id' follows default argument
```

1. **Fields without defaults come first.** The generated `__init__` is a normal function, and `def f(text="", chat_id)` isn't valid Python either (PY.M04.L01).
2. **No list, dict or set as a default.** You know why from PY.M02.L04: a default is created **once**, so every `Chat` would share one `member_ids` list. That's the exact class-attribute bug from L01 section 4. `@dataclass` refuses unhashable defaults outright instead of letting you hit it.

The fix is `field(default_factory=list)`: you pass a *function* (here the type `list` itself), and the generated `__init__` calls it for every new object:

```python
from dataclasses import dataclass, field


@dataclass
class Chat:
    title: str
    member_ids: list[int] = field(default_factory=list)


a = Chat("team")
b = Chat("family")
a.member_ids.append(1)
print(a, b)
```

```text
Chat(title='team', member_ids=[1]) Chat(title='family', member_ids=[])
```

Any zero-argument callable works: `default_factory=dict`, `default_factory=set`, or `default_factory=lambda: ["general"]`.

**Limitation:** the check only catches unhashable defaults. A default that's an instance of your own mutable (and therefore hashable by identity) class isn't detected, so use `default_factory` for any mutable default.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "A dataclass has the field `tags: dict[str, str] = {}`. When do you find out something is wrong?",
  "options": [
    "At import: @dataclass raises ValueError while creating the class",
    "Only when two instances exist and one of them changes its tags",
    "Never: dataclasses copy every default value for each new instance",
    "When a type checker runs; Python itself accepts the class"
  ], "answer": 0,
  "explanation": "@dataclass runs when the class statement executes, which is at import time, and it refuses list, dict and set defaults with ValueError. Use field(default_factory=dict)." }
```

## 3. `frozen=True`: value objects

Some things should never change after creation: an id, a reference, an amount of money. `frozen=True` makes field assignment raise an error, and `dataclasses.replace` gives you a modified **copy** instead:

```python
from dataclasses import dataclass, replace, FrozenInstanceError


@dataclass(frozen=True)
class ChatRef:
    chat_id: int
    peer_type: str = "group"


ref = ChatRef(42)
try:
    ref.chat_id = 43
except FrozenInstanceError as e:
    print("FrozenInstanceError:", e)
moved = replace(ref, chat_id=43)
print(ref, moved)
```

```text
FrozenInstanceError: cannot assign to field 'chat_id'
ChatRef(chat_id=42, peer_type='group') ChatRef(chat_id=43, peer_type='group')
```

Why bother? With reference semantics everywhere (L01 section 2), a mutable object handed to five functions can be changed by any of them. A frozen object can be shared freely, which is the value-receiver safety you're used to from Go. `replace` is the closest thing to Go's "copy the struct and change a field".

**Frozen is shallow.** It stops you rebinding a *field*; it doesn't freeze the object the field points to (PY.M02: mutating vs rebinding):

```quiz
{ "id": "q3", "type": "output", "label": "Debugging",
  "prompt": "What does this print?",
  "code": "from dataclasses import dataclass, field\n\n@dataclass(frozen=True)\nclass Chat:\n    title: str\n    member_ids: list[int] = field(default_factory=list)\n\nc = Chat(\"team\")\nc.member_ids.append(1)\nprint(c)",
  "answer": "Chat(title='team', member_ids=[1])",
  "explanation": "append mutates the list; it never assigns c.member_ids, so frozen doesn't object. For a truly immutable value, use immutable field types: a tuple[int, ...] instead of a list." }
```

## 4. Hashing: which dataclasses can be dict keys

Dict keys and set members must be hashable (PY.M03). The rule `@dataclass` follows:

- **`eq=True` (the default) and `frozen=True`**: `__hash__` is generated from the fields. Usable as a key.
- **`eq=True` and not frozen**: `__hash__` is set to `None`. A mutable object whose hash could change while it sits in a dict would corrupt the dict, so it's made unhashable.

```python
unread = {ChatRef(42): 3, ChatRef(7, "user"): 1}
print(unread[ChatRef(42)])

@dataclass
class User:
    user_id: int
    name: str

try:
    print({User(1, "ali")})
except TypeError as e:
    print("TypeError:", e)
```

```text
3
TypeError: unhashable type: 'User'
```

Note `unread[ChatRef(42)]` finds the entry with a *different but equal* object: equal fields give an equal hash. If a frozen dataclass holds a list, `hash()` fails with `unhashable type: 'list'`, which is another reason to use tuples in value objects.

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "With `@dataclass(frozen=True)` on `class Peer: user_id: int`, the code `seen = {Peer(1), Peer(2), Peer(1)}` works and `len(seen)` is 2.",
  "answer": true,
  "explanation": "frozen plus the generated __eq__ makes @dataclass generate __hash__ from the fields, so equal Peers hash equal and the set keeps one Peer(1). Without frozen=True, building the set would raise TypeError: unhashable type: 'Peer'." }
```

## 5. Sorting, hidden fields and validation

**`order=True`** generates `<`, `<=`, `>`, `>=` that compare the fields **as a tuple, in declaration order**. So field order is part of your design. **`field(compare=False)`** leaves a field out of `==` and ordering:

```python
@dataclass(order=True)
class Message:
    sent_at: int
    message_id: int
    text: str = field(compare=False)


inbox = [Message(1700000005, 2, "b"), Message(1700000001, 9, "a"), Message(1700000005, 1, "c")]
print([m.message_id for m in sorted(inbox)])
print(Message(1, 1, "x") == Message(1, 1, "y"))
```

```text
[9, 1, 2]
True
```

Sorted by `sent_at`, ties broken by `message_id`: the tie-break from PY.M03.L03, built into the type. The `True` on the last line looks wrong, but it's what `compare=False` asked for, so use it with care. **Alternative:** if you need different orders in different places, skip `order=True` and use `sorted(inbox, key=lambda m: (m.sent_at, m.message_id))`.

**`field(repr=False)`** keeps secrets out of logs and tracebacks. **`__post_init__`** runs right after the generated `__init__`, which makes it the place for validation and normalisation (what you'd put in `NewX` in Go):

```python
from dataclasses import asdict


@dataclass
class Account:
    login: str
    password_hash: str = field(repr=False)

    def __post_init__(self) -> None:
        self.login = self.login.strip().lower()
        if not self.login:
            raise ValueError("login must not be empty")


acc = Account("  Ali ", "pbkdf2$...")
print(acc)
print(asdict(acc))
try:
    Account("   ", "x")
except ValueError as e:
    print("ValueError:", e)
```

```text
Account(login='ali')
{'login': 'ali', 'password_hash': 'pbkdf2$...'}
ValueError: login must not be empty
```

`asdict` converts the object (recursively) to a dict, for example right before `json.dumps`. Note that `repr=False` hides the field only from the repr; `asdict` still includes it.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "from dataclasses import dataclass\n\n@dataclass(order=True)\nclass Ticket:\n    priority: int\n    created: int\n\nqueue = [Ticket(2, 10), Ticket(1, 30), Ticket(2, 5)]\nprint([(t.priority, t.created) for t in sorted(queue)])",
  "answer": "[(1, 30), (2, 5), (2, 10)]",
  "explanation": "order=True compares (priority, created) as tuples: priority first, then created breaks the tie between the two priority-2 tickets." }
```

## 6. Annotations are required, but not checked

A dataclass needs the annotation to know a field exists, but it never checks the value against it:

```python
@dataclass
class User:
    user_id: int
    name: str

u = User("not-an-int", 5)
print(u)
```

```text
User(user_id='not-an-int', name=5)
```

No error. Python doesn't enforce type hints anywhere at runtime; the next lesson explains what they're for. If a value comes from outside (JSON, a form, a database row) and must be validated, check it yourself in `__post_init__`, or use a validating library at the boundary (Pydantic, WEB.M02).

```quiz
{ "id": "q6", "type": "output",
  "prompt": "What does this print?",
  "code": "from dataclasses import dataclass\n\n@dataclass\nclass Limit:\n    per_minute: int\n\nprint(Limit(\"60\").per_minute * 2)",
  "answer": "6060",
  "explanation": "The annotation says int, but nothing converts or checks: per_minute is the string \"60\", and a string times 2 repeats it. Hints don't convert values." }
```

## 7. Your turn

Model a value type with the right options, a strict parser and a mutable container with a safe default. Before you code, decide which dataclass options give you ordering, immutability and hashing, and list the inputs `parse` must reject.

```exercise
PY.M05.L02.E1
```
