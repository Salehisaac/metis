---
{
  "id": "PY.M05.L04",
  "title": "Composition vs inheritance",
  "difficulty": "intermediate",
  "minutes": 50,
  "prerequisites": ["PY.M05.L03"],
  "objectives": [
    "Write a subclass with super().__init__ and an override, and compare it precisely with Go struct embedding",
    "Predict which method runs when a base-class method calls self.something() that a subclass overrides",
    "Explain why subclassing a built-in collection to enforce a rule leaks, and replace it with composition",
    "Design a class that has its collaborators (has-a) and delegates to them explicitly",
    "Choose composition or inheritance for a given situation and justify the choice in one or two sentences"
  ],
  "why": "Python makes inheritance easy to type and hard to live with: one class line gives you every method of the parent, including ones that break your rules, and the parent's code starts calling your overrides. Go never let you do that, which is good news: your Go instincts (small interfaces, embedding as composition) are the right default here too. This lesson shows when to follow them and the few places where inheritance is the right tool.",
  "applications": [
    "Service classes that hold a repository, a sender and a clock instead of inheriting from them",
    "Exception hierarchies (ChatError → NotAMember) that callers can catch at the right level",
    "Spotting a fragile subclass in code review"
  ],
  "exercises": ["PY.M05.L04.E1"],
  "sources": [
    {
      "title": "Python Tutorial: Classes (Inheritance)",
      "url": "https://docs.python.org/3.12/tutorial/classes.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "Derived classes may override methods of their base classes",
        "A base-class method can be called directly as BaseClassName.methodname(self, arguments)",
        "isinstance(obj, cls) is True for instances of cls or of classes derived from it",
        "Python supports multiple inheritance"
      ]
    },
    {
      "title": "Built-in Functions: super",
      "url": "https://docs.python.org/3.12/library/functions.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "super() returns a proxy object that delegates method calls to a parent or sibling class",
        "Inside a class, super().method(arg) is the usual form; the zero-argument form only works inside a class definition"
      ]
    },
    {
      "title": "abc: Abstract Base Classes",
      "url": "https://docs.python.org/3.12/library/abc.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["A class with unimplemented abstract methods cannot be instantiated"]
    }
  ]
}
---
## 1. Inheritance in Python, next to Go embedding

```python
class User:
    def __init__(self, user_id: int, name: str) -> None:
        self.user_id = user_id
        self.name = name

    def display_name(self) -> str:
        return self.name

    def greeting(self) -> str:
        return f"Hi, {self.display_name()}!"


class Bot(User):
    def __init__(self, user_id: int, name: str, owner_id: int) -> None:
        super().__init__(user_id, name)
        self.owner_id = owner_id

    def display_name(self) -> str:
        return f"{self.name} [bot]"


b = Bot(99, "weather", owner_id=1)
print(b.greeting())
print(isinstance(b, User), b.owner_id)
```

```text
Hi, weather [bot]!
True 1
```

- `class Bot(User)` means Bot **inherits** everything User has.
- `super().__init__(user_id, name)` runs the parent's initialiser on this same object. `super()` gives you the parent's version of a method you've overridden.
- `display_name` is **overridden**: Bot's version replaces User's for Bot objects.
- `isinstance(b, User)` is True: a Bot can go anywhere a User is expected.

The nearest Go is embedding, `type Bot struct { User; OwnerID int }`. Go promotes `User`'s methods to `Bot`, and `Bot` satisfies any interface `User` satisfies. But you can't pass a `Bot` where the concrete type `User` is required, and the second difference matters even more:

```go
func (u *User) Greeting() string    { return "Hi, " + u.DisplayName() + "!" }
func (b *Bot) DisplayName() string  { return b.Name + " [bot]" }

b := &Bot{User: User{Name: "weather"}, OwnerID: 1}
fmt.Println(b.Greeting())  // Hi, weather!
```

In Go, the promoted `Greeting` runs with the inner `*User` as its receiver, so it calls `User.DisplayName`. In Python, `self` is always the whole object (the Bot), so `self.display_name()` finds **Bot's override**. Same code shape, different output.

**Common mistake:** forgetting `super().__init__(...)` in the subclass. Python doesn't call the parent's `__init__` for you, so its attributes never get set:

```quiz
{ "id": "q1", "type": "output", "label": "Debugging",
  "prompt": "What does this print?",
  "code": "class User:\n    def __init__(self, user_id: int, name: str) -> None:\n        self.user_id = user_id\n        self.name = name\n\nclass Bot(User):\n    def __init__(self, user_id: int, name: str, owner_id: int) -> None:\n        self.owner_id = owner_id\n\nb = Bot(99, \"weather\", 1)\nprint(b.owner_id, hasattr(b, \"name\"))",
  "answer": "1 False",
  "explanation": "Bot defines its own __init__, which replaces User's, and never calls super().__init__(user_id, name). So name and user_id are never assigned. The object exists but is half built, and the error shows up later as an AttributeError somewhere else." }
```

## 2. The parent calls your overrides

That last difference has a name: **dynamic dispatch through `self`**. Every `self.method()` call inside the parent is looked up on the actual object, so a subclass can change the parent's behaviour from the inside:

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "class Notification:\n    def prefix(self) -> str:\n        return \"info\"\n\n    def render(self, text: str) -> str:\n        return f\"[{self.prefix()}] {text}\"\n\nclass Urgent(Notification):\n    def prefix(self) -> str:\n        return \"URGENT\"\n\nn = Urgent()\nprint(n.render(\"db down\"), Notification.render(n, \"x\"))",
  "answer": "[URGENT] db down [URGENT] x",
  "explanation": "render is Notification's code, but self is the Urgent object, so self.prefix() finds Urgent.prefix. Even calling Notification.render(n, ...) explicitly doesn't help: what matters is the object passed as self." }
```

Sometimes that's exactly what you want: a base class with a fixed algorithm and "hooks" for subclasses to fill in (the ABC pattern from L03). But it also means a subclass depends on **which parent methods call which**, and that's an internal detail of the parent. If the parent's author changes `render` to stop calling `prefix`, every subclass silently breaks. This is the **fragile base class** problem, and Go avoids it by not having dispatch through embedding at all.

## 3. Subclassing a built-in to add a rule: the trap

A tempting shortcut: "I want a list that stores usernames lowercase, so subclass `list` and override `append`."

```python
class Usernames(list):
    """A list of usernames, always stored lowercase."""

    def append(self, name: str) -> None:
        super().append(name.lower())


names = Usernames()
names.append("Ali")
names.extend(["Sara"])
names += ["REZA"]
names.insert(0, "Mina")
print(names, type(names).__name__)
```

```text
['Mina', 'ali', 'Sara', 'REZA'] Usernames
```

Only `append` lowercased. `extend`, `+=` and `insert` are separate methods of the built-in `list`, implemented in C, and they don't go through your `append`. So the rule holds on one path out of many. (Section 2 said parents call your overrides, but only where the parent's code actually calls that method. The built-in list's other methods don't call `append`.) Inheriting gave `Usernames` the **whole** list interface, around 11 public methods plus slicing and operators, and each one is a way around the rule. You'd have to find and override every one of them, and the list keeps working against you.

The underlying question is **is-a vs has-a**. A list of usernames with a rule isn't "a list that anyone may change in any list way". It's a thing that **has** a list and allows only the changes that keep the rule.

## 4. Composition: has-a, with explicit delegation

Composition means the object holds its collaborators as attributes and exposes only the operations it supports. Here's a chat service that has a sender (the L03 protocol) and a history:

```python
from collections.abc import Iterator
from typing import Protocol


class Sender(Protocol):
    def send(self, chat_id: int, text: str) -> None: ...


class ChatService:
    """Has a sender and a history list; exposes only what it supports."""

    def __init__(self, chat_id: int, sender: Sender) -> None:
        self.chat_id = chat_id
        self._sender = sender
        self._history: list[str] = []

    def post(self, text: str) -> None:
        text = text.strip()
        if not text:
            raise ValueError("empty message")
        self._history.append(text)
        self._sender.send(self.chat_id, text)

    def __len__(self) -> int:
        return len(self._history)

    def __iter__(self) -> Iterator[str]:
        return iter(self._history)
```

```python
fake = RecordingSender()          # the test fake from L03
chat = ChatService(7, fake)
chat.post(" hello ")
chat.post("bye")
print(len(chat), list(chat), fake.sent)
print(hasattr(chat, "append"), "hello" in chat)
```

```text
2 ['hello', 'bye'] [(7, 'hello'), (7, 'bye')]
False True
```

What composition bought:

- **A small surface.** `ChatService` has `post` and nothing else that changes state. There's no `append` that skips the validation.
- **Swappable parts.** The sender is passed in, so tests use a fake. Inheriting from a `TelegramSender` would hard-wire the network into every chat.
- **Built-in behaviour where you want it.** Special methods like `__len__` and `__iter__` make `len()`, `for`, `list()` and even `in` work, without exposing mutation.
- **No dispatch surprises.** `ChatService` calls `self._sender.send(...)`, a plain call on another object. Nothing it depends on is overridden behind its back.

**The cost:** Python has no automatic method promotion like Go embedding, so each operation you expose is a method you write. That's usually a feature: you're writing the API you mean to offer. (Tricks like `__getattr__` forwarding everything exist, but they bring back the "whole interface" problem from section 3.)

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "`ChatService` must store messages in Redis in production and in memory in tests. Which design fits best?",
  "options": [
    "`class ChatService(RedisStore)`, plus a `TestChatService(InMemoryStore)` copy for tests",
    "ChatService takes any store with save/last in `__init__` and calls it",
    "`class ChatService(RedisStore, InMemoryStore)` with a flag that picks a parent",
    "A module-level global `STORE` that tests overwrite before each test"
  ], "answer": 1,
  "explanation": "Composition plus a protocol: the service has a store and doesn't care which. Inheriting ties the service to one storage, multiple inheritance with a flag mixes both into every object, and a global hides the dependency and leaks between tests." }
```

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "If class A holds a B in `self._b`, every method of B is automatically callable on A objects, like promoted methods with Go embedding.", "answer": false,
  "explanation": "Python never promotes methods from an attribute. A has only the methods you write on A, for example def post(self, ...): self._b.send(...). Inheritance is the only automatic way to get another class's methods." }
```

## 5. When inheritance is the right tool

Inheritance is fine, and sometimes required, when the subclass really **is** a specialised version of the parent, the parent was **designed** to be extended, and you mean to accept the parent's whole interface. The cases you'll meet most:

- **Exceptions.** Every exception class inherits from `Exception`, and a small hierarchy lets callers choose how specific to be (PY.M04):

```python
class ChatError(Exception):
    pass


class NotAMember(ChatError):
    pass


class ChatFull(ChatError):
    pass
```

- **Base classes a framework tells you to subclass**: an ABC with abstract hooks (L03), test classes, and later Pydantic's `BaseModel` (WEB.M02). Their authors designed them for it and documented which methods to override.
- **A small family of types** sharing real behaviour, where every subclass is a full substitute for the parent (any code written for `User` works correctly with a `Bot`).

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "class ChatError(Exception):\n    pass\n\nclass NotAMember(ChatError):\n    pass\n\nclass ChatFull(ChatError):\n    pass\n\ndef join(chat_id: int) -> None:\n    raise ChatFull(f\"chat {chat_id} is full\")\n\ntry:\n    join(7)\nexcept NotAMember:\n    print(\"not a member\")\nexcept ChatError as e:\n    print(type(e).__name__, isinstance(e, Exception))",
  "answer": "ChatFull True",
  "explanation": "ChatFull isn't a NotAMember, so the first except is skipped. It is a ChatError (its parent), so the second matches. The object's real type is still ChatFull, and through the chain it is also an Exception." }
```

**Rules of thumb**, in order:

1. Need another object's *behaviour*? **Hold it** (composition) and call it.
2. Need several types to be *interchangeable*? Describe the shared methods with a **Protocol** (L03). No common parent required.
3. Need to *extend a class built for extension* (Exception, an ABC, a framework base)? **Inherit**, call `super().__init__`, and override only the documented hooks.
4. Tempted to inherit from `list`, `dict` or a concrete class you don't control, just to add a rule or reuse a few methods? That's case 1 in disguise.

Python also allows inheriting from **several** classes at once (multiple inheritance, sometimes used for small "mixin" classes). You'll recognise it in library code. Don't reach for it in your own designs; composition covers the same needs with less to reason about.

```quiz
{ "id": "q6", "type": "choice", "label": "Application",
  "prompt": "You need an `AuditedDict` that logs every write for compliance. A teammate proposes `class AuditedDict(dict)` overriding `__setitem__`. What's the main risk?",
  "options": [
    "None: overriding `__setitem__` covers every way to write to a dict",
    "dict can't be subclassed, so the class statement fails",
    "Overriding `__setitem__` makes every read noticeably slower",
    "`update()` and `setdefault()` skip `__setitem__`, so writes escape the log"
  ], "answer": 3,
  "explanation": "Same lesson as the Usernames list: the built-in's other methods (update, setdefault, |=, the constructor) don't call your override. For a compliance rule, wrap a dict and expose only the writes you audit." }
```

## 6. Your turn

The exercise gives you a class that inherits from `list` to enforce a rule, with a bug report saying the rule leaks. Refactor it to composition: decide what the class *has*, which operations it should offer, and put the rule in exactly one place.

```exercise
PY.M05.L04.E1
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "A colleague writes `class OrderService(PostgresRepository)` so the service can call `self.insert(...)` directly. In two or three sentences, argue for composition instead, and say what it changes in tests.",
  "model": "OrderService is not a kind of repository; it uses one. Inheriting gives it every repository method as part of its public interface, ties it to Postgres, and lets the repository's internals call into overrides. With composition, `__init__(self, repo: OrderRepo)` stores the repo and the service calls self._repo.insert(...). Tests pass an in-memory fake that satisfies the same small protocol, with no database and no subclassing.",
  "explanation": "Has-a beats is-a when you need behaviour, not substitutability." }
```
