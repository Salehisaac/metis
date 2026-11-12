---
{ "id": "PY.M05.A", "module": "PY.M05", "title": "PY.M05 module assessment: classes, dataclasses, typing", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before PY.M06.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?",
  "code": "class Session:\n    data = {}\n\n    def set(self, key: str, value: str) -> None:\n        self.data[key] = value\n\na = Session()\nb = Session()\na.set(\"lang\", \"fa\")\nprint(b.data)",
  "answer": "{'lang': 'fa'}",
  "explanation": "data is a class attribute: one dict created when the class is defined and shared by every Session. self.data finds it on the class, and set mutates it. Create per-object state in __init__: self.data = {}." }
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "What does this print?",
  "code": "from dataclasses import dataclass, replace\n\n@dataclass(frozen=True)\nclass Point:\n    x: int\n    y: int\n\np = Point(1, 2)\nq = replace(p, y=5)\nprint(p, q == Point(1, 5), p is q)",
  "answer": "Point(x=1, y=2) True False",
  "explanation": "replace builds a new object and leaves p unchanged (it's frozen anyway). The generated __eq__ compares fields, so q equals Point(1, 5), but p and q are different objects." }
```

```quiz
{ "id": "a3", "type": "truefalse",
  "prompt": "Calling `def limit(n: int) -> int: ...` as `limit(\"3\")` raises TypeError before the function body runs.", "answer": false,
  "explanation": "Python doesn't enforce type hints at runtime. The body runs with n == \"3\"; an error appears only if some operation inside fails. Checking hints is the job of an optional type checker, and validating input is your job (or a library's)." }
```

```quiz
{ "id": "a4", "type": "output",
  "prompt": "What does this print?",
  "code": "from abc import ABC, abstractmethod\nfrom typing import Protocol, runtime_checkable\n\n@runtime_checkable\nclass Closer(Protocol):\n    def close(self) -> None: ...\n\nclass Resource(ABC):\n    @abstractmethod\n    def close(self) -> None: ...\n\nclass Conn:\n    def close(self) -> None:\n        pass\n\nprint(isinstance(Conn(), Closer), isinstance(Conn(), Resource))",
  "answer": "True False",
  "explanation": "A Protocol is structural, like a Go interface: Conn has close, so it matches. An ABC is nominal: Conn never inherits from Resource (and isn't registered), so it isn't one." }
```

```quiz
{ "id": "a5", "type": "choice",
  "prompt": "Why does a dataclass need `labels: list[str] = field(default_factory=list)` instead of `labels: list[str] = []`?",
  "options": [
    "Type hints require a factory for generic types such as `list[str]`",
    "`= []` works too, but `default_factory` is faster",
    "One `[]` would be shared by all instances, so @dataclass rejects it",
    "`field()` makes the list immutable after `__init__`"
  ], "answer": 2,
  "explanation": "It's the mutable-default trap from PY.M02: a default value is created once. @dataclass rejects list, dict and set defaults with ValueError, and default_factory calls list() for each new object." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "You need a `MessageQueue` that keeps messages in order and rejects messages over 4096 characters. A teammate writes `class MessageQueue(list)` overriding `append`. Do you approve? Justify in two or three sentences and say what you'd write instead.",
  "model": "No. Inheriting from list exposes every list method: extend, insert, += and item assignment all bypass the overridden append, so oversized messages can still get in. Use composition: MessageQueue holds a private list, offers only push (which validates) plus pop/__len__/__iter__ as needed, and so has exactly one entry point for the rule.",
  "explanation": "Is-a list means accepting the whole list interface; has-a list lets you expose only the operations that keep the rule." }
```
