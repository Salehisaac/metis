---
{
  "id": "PY.M05.L01",
  "title": "Classes vs Go structs and methods",
  "difficulty": "beginner",
  "minutes": 45,
  "prerequisites": ["PY.M02.L03", "PY.M04.L02"],
  "objectives": [
    "Translate a Go struct with methods and a NewX constructor into a Python class with __init__, self and a @classmethod",
    "Predict the effect of mutating an object through self, a second name or a function argument (always shared, like a pointer receiver)",
    "Tell instance attributes from class attributes and avoid the shared-mutable-class-attribute bug",
    "Explain why a plain class prints as <... object at 0x...> and why == is identity, and fix the printing with __repr__",
    "Use @property for a computed read-only attribute"
  ],
  "why": "Every FastAPI app, test fake and service object you'll write is a class. You already think in structs and methods; this lesson maps them one to one and shows the three places where Python behaves differently from Go: no value receivers, no field declarations, and == that compares identity by default.",
  "applications": [
    "Domain objects (User, Chat, Message) with validation in the constructor",
    "Alternate constructors such as from_row or from_dict for database rows and JSON",
    "Service objects that hold their dependencies as attributes"
  ],
  "exercises": ["PY.M05.L01.E1"],
  "sources": [
    {
      "title": "Python Tutorial: Classes",
      "url": "https://docs.python.org/3.12/tutorial/classes.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "The name self is only a convention",
        "Instantiation automatically calls __init__",
        "x.f() is exactly equivalent to MyClass.f(x)",
        "Instance variables are per instance; class variables are shared; a mutable class variable (the tricks list) is shared by all instances",
        "Attribute lookup prefers the instance over the class",
        "Nothing enforces data hiding; an underscore prefix marks a non-public name by convention"
      ]
    },
    {
      "title": "Built-in Functions: classmethod, property",
      "url": "https://docs.python.org/3.12/library/functions.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "A class method receives the class as an implicit first argument and can be called on the class or an instance",
        "@property turns a method into a getter for a read-only attribute with the same name"
      ]
    },
    {
      "title": "Expressions: Value comparisons",
      "url": "https://docs.python.org/3.12/reference/expressions.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["The default behaviour of == and != is based on object identity"]
    },
    {
      "title": "Glossary: method",
      "url": "https://docs.python.org/3.12/glossary.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["A method called on an instance gets the instance as its first argument, usually named self"]
    }
  ]
}
---
## 1. A struct with methods becomes a class

The Go you know:

```go
type User struct {
    ID   int
    Name string
}

func (u *User) Rename(newName string) { u.Name = newName }
```

The Python version:

```python
class User:
    def __init__(self, user_id: int, name: str) -> None:
        self.user_id = user_id
        self.name = name

    def rename(self, new_name: str) -> None:
        self.name = new_name


ali = User(1, "ali")
ali.rename("Ali")
print(ali.name)
User.rename(ali, "ALI")
print(ali.name)
```

```text
Ali
ALI
```

The mapping:

| Go | Python |
|---|---|
| `type User struct {...}` | `class User:` |
| field list | attributes **assigned** in `__init__` (`self.name = name`) |
| receiver `(u *User)` | first parameter `self`, written explicitly in every method |
| `u.Rename("x")` | `ali.rename("x")`, which is exactly `User.rename(ali, "x")` |
| `User{ID: 1, Name: "ali"}` | `User(1, "ali")`: calling the class creates the object and runs `__init__` on it |

`self` is just the name everyone uses for the receiver; Python passes the object as the first argument whatever you call it. `__init__` isn't a constructor that returns something; it fills in an object that already exists, and it must return `None`.

**Difference 1: there are no field declarations.** An attribute exists because some code assigned it. A typo doesn't fail to compile; it quietly creates a new attribute:

```python
ali.nmae = "typo"
print(ali.name, ali.nmae)
```

```text
ALI typo
```

The next lesson (dataclasses) gets you back a declared field list.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "class Counter:\n    def __init__(self) -> None:\n        self.n = 0\n\n    def inc(self) -> None:\n        self.n += 1\n\nc = Counter()\nc.inc()\nCounter.inc(c)\nc.inc()\nprint(c.n)",
  "answer": "3",
  "explanation": "c.inc() and Counter.inc(c) are the same call: the object is passed as self either way. Three calls, so n is 3." }
```

## 2. Every receiver is a pointer receiver

In Go you choose: `func (u User)` gets a copy, `func (u *User)` shares the caller's struct. Python has no choice to make. A variable holds a **reference** to the object (PY.M02: names are labels), so `self`, a second variable and a function parameter all point at the same object:

```python
def shout_name(u: User) -> None:
    u.name = u.name.upper()


ali = User(1, "ali")
admin = ali            # a second label, not a copy
admin.name = "boss"
print(ali.name)
shout_name(ali)
print(ali.name, admin is ali)
```

```text
boss
BOSS True
```

This is the same aliasing you practised with lists in PY.M02, just with your own type. If you want a Go-style value copy, you have to make one explicitly (`copy.copy(obj)`, or for dataclasses `dataclasses.replace`, next lesson).

**Common mistake:** "I passed the user to a helper and it changed my original." Every method and function that assigns `obj.attr = ...` changes the one shared object.

```quiz
{ "id": "q2", "type": "output", "label": "Debugging",
  "prompt": "What does this print?",
  "code": "class Message:\n    def __init__(self, text: str) -> None:\n        self.text = text\n\ndef redact(m: Message) -> Message:\n    m.text = \"***\"\n    return m\n\noriginal = Message(\"my password is hunter2\")\nsafe = redact(original)\nprint(original.text, safe is original)",
  "answer": "*** True",
  "explanation": "redact receives a reference to the same object, changes it and returns that same object. There was never a copy, so the original is redacted too. To keep it, build a new object: return Message(\"***\")." }
```

## 3. NewX becomes `__init__` plus classmethods

Go has no constructors, so you write `func NewChat(id int, title string) (*Chat, error)` and validate there. In Python:

- **Validation goes in `__init__`**, and a bad value **raises** (PY.M04) instead of returning an error. If `__init__` raises, the caller never gets an object, so no half-built object leaks out.
- **Extra constructors are `@classmethod`s**, the equivalent of a second `NewChatFromRow`. A classmethod receives the **class** as its first argument (named `cls` by convention) instead of an instance, and calls `cls(...)` to build the object.

```python
class Chat:
    def __init__(self, chat_id: int, title: str) -> None:
        title = title.strip()
        if not title:
            raise ValueError("chat title must not be empty")
        self.chat_id = chat_id
        self.title = title
        self.member_ids: list[int] = []

    @classmethod
    def from_row(cls, row: dict) -> "Chat":
        return cls(row["id"], row["title"])


c = Chat.from_row({"id": 7, "title": "  backend  "})
print(c.title, c.member_ids)
try:
    Chat(8, "   ")
except ValueError as e:
    print("ValueError:", e)
```

```text
backend []
ValueError: chat title must not be empty
```

Why `cls(...)` and not `Chat(...)`? If someone subclasses `Chat`, `SubChat.from_row(...)` then builds a `SubChat`. The quotes in `-> "Chat"` are needed because the class name doesn't exist yet while its body is being defined.

**Alternative:** a module-level function `def new_chat(...)` works too, and is fine for one-off helpers. Prefer a classmethod when the constructor belongs to the type, because callers find it as `Chat.from_row`.

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "You need to build a `User` from a JSON dict, `{\"id\": 1, \"name\": \"ali\"}`, in addition to the normal `User(1, \"ali\")`. What's the idiomatic Python?",
  "options": [
    "A second `__init__` method that takes a dict",
    "A function `NewUser` that returns `(user, error)`",
    "One `__init__` that checks with isinstance whether it got a dict or two values",
    "A `@classmethod` `from_dict(cls, data)` returning `cls(data[\"id\"], data[\"name\"])`"
  ], "answer": 3,
  "explanation": "Python has no overloading: a second `def __init__` just replaces the first. An alternate constructor is a classmethod that calls cls(...). Errors are raised, not returned." }
```

## 4. Instance attributes vs class attributes

Anything assigned **in the class body** (outside methods) is a **class attribute**: one value, stored on the class, shared by every instance. Anything assigned to `self.x` is an **instance attribute**. When you read `obj.x`, Python looks on the instance first, then on the class.

That's handy for constants, and a trap for mutable values:

```python
class Chat:
    members = []          # class attribute: ONE list, shared

    def __init__(self, title: str) -> None:
        self.title = title

    def join(self, user_id: int) -> None:
        self.members.append(user_id)


team = Chat("team")
family = Chat("family")
team.join(1)
family.join(2)
print(team.members, family.members, team.members is Chat.members)
```

```text
[1, 2] [1, 2] True
```

Neither instance has its own `members`, so `self.members` finds the class's list, and both chats append to it. It's the same bug as the mutable default argument from PY.M02.L04: a list created **once** at definition time, then shared. The fix is to create the list per object, in `__init__`: `self.members = []`, as the `Chat` in section 3 does.

There's no such trap in Go, because struct fields are always per value. Go's closest equivalent of a class attribute is a package-level variable.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "class Limits:\n    max_len = 100\n\na = Limits()\nb = Limits()\na.max_len = 5\nprint(a.max_len, b.max_len, Limits.max_len)",
  "answer": "5 100 100",
  "explanation": "Assigning a.max_len creates an instance attribute on a only; lookup finds it before the class attribute. b has none, so b.max_len reads the class value. Mutating a shared list (append) is different from assigning: assigning never touches the class." }
```

## 5. Printing and comparing: why a plain class is unhelpful

Go prints structs with `%+v` and compares them with `==` field by field. A plain Python class does neither:

```python
print(User(1, "ali"))
print(User(1, "ali") == User(1, "ali"))
```

```text
<__main__.User object at 0x73b3f4f82720>
False
```

- **Printing** shows the class name and a memory address (it changes every run), because Python doesn't know which attributes matter.
- **`==` defaults to identity**: two objects are equal only if they're the *same object* (`a is b`). Equal-looking contents don't count.

You fix printing by defining `__repr__` (the developer view that the REPL, `print` of a list and pytest failure messages use):

```python
class Chat:
    ...
    def __repr__(self) -> str:
        return f"Chat(chat_id={self.chat_id!r}, title={self.title!r})"
```

```text
Chat(chat_id=7, title='backend')
```

`!r` inside an f-string uses the repr of the value, so strings get their quotes. Writing `__repr__` and `__eq__` by hand for every class is tedious and easy to get wrong when you add a field. That's exactly what `@dataclass` generates for you in the next lesson.

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "A test does `assert load_user(1) == User(1, \"ali\")` on a plain class with only `__init__`. load_user returns a fresh User(1, \"ali\"). What happens?",
  "options": [
    "It passes: all the attributes are equal",
    "It fails: == compares identity here",
    "TypeError: User objects can't be compared with ==",
    "It passes only if the class defines __repr__"
  ], "answer": 1,
  "explanation": "Without __eq__, == falls back to identity. __repr__ only changes how the failure is printed. A dataclass, or your own __eq__, gives field-by-field equality." }
```

## 6. Underscores and `@property`

**Privacy by convention.** Go hides a field by starting it with a lowercase letter, and the compiler enforces it. Python enforces nothing: a leading underscore (`self._cache`) means "internal, don't touch from outside", and everyone respects it.

**Computed attributes.** `@property` turns a method into a read-only attribute: the caller writes `chat.member_count` with no parentheses, and the method runs each time.

```python
class Chat:
    ...
    @property
    def member_count(self) -> int:
        return len(self.member_ids)


c.member_ids.append(42)
print(c.member_count)
try:
    c.member_count = 5
except AttributeError as e:
    print("AttributeError:", e)
```

```text
1
AttributeError: property 'member_count' of 'Chat' object has no setter
```

Why not just a method? Because Python style is to start with plain attributes and **no getters**. If a value later needs computing or checking, you change it to a property and no caller has to change. In Go you'd have written `GetX()` up front, just in case. Use properties for cheap, side-effect-free values. Anything slow or with side effects (a database query) should stay a method call, so it looks like one.

```quiz
{ "id": "q6", "type": "truefalse",
  "prompt": "Code outside the class can still read and change `obj._token`: the leading underscore is only a convention.",
  "answer": true,
  "explanation": "Python has no compiler-enforced visibility like Go's lowercase names. The underscore signals 'internal, may change without notice', and well-behaved code respects it, but nothing stops access." }
```

## 7. Your turn

Write a small class from a spec. It uses all of the above: state created in `__init__` (section 4), a classmethod constructor that mustn't alias its input (sections 2 and 3), errors raised before anything changes, a `__repr__` (section 5) and a property (section 6). Read the edge cases in the exercise before you start.

```exercise
PY.M05.L01.E1
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "In Go you'd write `func (s *Session) Touch()` with a pointer receiver so the change sticks. Why is there no pointer/value receiver choice in Python, and what's the consequence when you pass objects to helpers?",
  "model": "Python variables hold references to objects, and self is just another reference, so every method works on the shared object (like a pointer receiver). Passing an object to a function passes the reference too. Any mutation inside a helper is visible to the caller; to get value semantics you must copy explicitly (copy.copy, dataclasses.replace, or build a new object).",
  "explanation": "There is no implicit copy anywhere in Python: not on assignment, not on calls, not on method receivers." }
```
