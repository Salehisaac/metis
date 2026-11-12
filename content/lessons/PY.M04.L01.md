---
{
  "id": "PY.M04.L01",
  "title": "Parameters: positional, keyword, defaults, *args/**kwargs",
  "difficulty": "beginner",
  "minutes": 40,
  "prerequisites": ["PY.M03"],
  "objectives": [
    "Predict which parameter receives each argument in a call that mixes positional and keyword arguments",
    "Explain when a default value is evaluated, and use None as the default for a mutable value",
    "Use *args and **kwargs in a def (collect) and * and ** in a call (unpack)",
    "Design a signature with keyword-only (*) and positional-only (/) parameters so that wrong calls fail with TypeError"
  ],
  "why": "Go has one way to pass arguments: by position, all of them, every time. Python lets the caller name arguments, skip ones with defaults, and pass any number of extras. That flexibility is why Python APIs (FastAPI, pytest, SQLAlchemy) look the way they do. A well-designed signature also makes wrong calls fail immediately instead of silently swapping two strings.",
  "applications": [
    "Readable calls such as connect(host, timeout=2.0) instead of a row of unnamed values",
    "Forcing callers to name easily-confused arguments (source/target, user_id/order_id)",
    "Wrapper functions that pass *args/**kwargs through to another function",
    "Reading library signatures such as pytest's raises(expected_exception, *, match=...)"
  ],
  "exercises": ["PY.M04.L01.E1"],
  "sources": [
    {
      "title": "The Python Tutorial, 4.9 More on Defining Functions",
      "url": "https://docs.python.org/3.12/tutorial/controlflow.html#more-on-defining-functions",
      "version": "Python 3.12 docs; examples run with Python 3.12.3",
      "verified": "2026-11-12",
      "claims": [
        "Default values are evaluated at the point of function definition, and only once, which matters for mutable defaults; use None instead",
        "In a call, keyword arguments must follow positional arguments, and no argument may receive a value more than once",
        "*name receives a tuple of extra positional arguments; **name receives a dict of extra keyword arguments; *name must come before **name",
        "Parameters after *args are keyword-only",
        "A bare * marks the following parameters keyword-only; parameters before / are positional-only",
        "* and ** unpack a list/tuple and a dict into arguments in a call"
      ]
    }
  ]
}
---
## 1. Positional and keyword arguments

In Go, `Connect("db", 5432, 5*time.Second)` matches arguments to parameters by position only. Python also lets the caller match them **by name**:

```python
def connect(host, port=5432, timeout=5.0):
    return f"{host}:{port} timeout={timeout}"

print(connect("db"))                       # port and timeout use their defaults
print(connect("db", 6432))                 # by position: 6432 goes to port
print(connect("db", timeout=1.5))          # skip port, name timeout
print(connect(timeout=1.5, host="cache"))  # keyword order doesn't matter
```

```console
db:5432 timeout=5.0
db:6432 timeout=5.0
db:5432 timeout=1.5
cache:5432 timeout=1.5
```

Python fills the parameters in two passes: first the positional arguments from left to right, then the keyword arguments by name. Two rules follow from that:

- **Keyword arguments come after positional ones** in a call. `connect(host="db", 6432)` is a `SyntaxError`.
- **No parameter gets two values.** `connect("db", host="x")` fails with `TypeError: connect() got multiple values for argument 'host'`, because `"db"` already went to `host` by position.

A missing required argument is also a `TypeError`, raised *before* the function body runs: `connect(port=1)` gives `connect() missing 1 required positional argument: 'host'`. This is Python's runtime version of Go's compile-time signature check.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "def connect(host, port=5432, timeout=5.0):\n    return f\"{host}:{port} timeout={timeout}\"\n\nprint(connect(\"api\", 80, timeout=2))",
  "answer": "api:80 timeout=2",
  "explanation": "\"api\" goes to host and 80 to port by position, then timeout is set by name. The 2 stays an int, because Python doesn't convert it to match the default's type." }
```

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "With `def connect(host, port=5432, timeout=5.0)`, which call raises TypeError?",
  "options": ["connect(\"db\", 6432, 1.0)", "connect(port=6432, host=\"db\")", "connect(\"db\", port=6432, host=\"db2\")", "connect(\"db\", timeout=0)"], "answer": 2,
  "explanation": "\"db\" already filled host by position, so host=\"db2\" would give it a second value: 'got multiple values for argument host'. The other calls are valid. Keyword order doesn't matter, and 0 is a perfectly good timeout value." }
```

## 2. Defaults are evaluated once, at `def` time

A default isn't re-computed on each call. Python evaluates it **once, when the `def` statement runs**, and stores the value with the function:

```python
limit = 10

def page(size=limit):
    return size

limit = 99
print(page())   # 10: the default was taken when def ran
```

For numbers and strings that's harmless. For a **mutable** default such as `[]` or `{}`, every call shares the same object. That's the mutable-default-argument trap from PY.M02.L04. The fix is the same as there: use `None` as the default and create the object inside the function.

```python
def add_tag(tag, tags=None):
    if tags is None:
        tags = []          # a new list on every call
    tags.append(tag)
    return tags
```

Test it with `is None`, not with truthiness: an empty list passed by the caller is falsy, but it's still "given".

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "unit = \"s\"\n\ndef fmt(n, suffix=unit):\n    return f\"{n}{suffix}\"\n\nunit = \"ms\"\nprint(fmt(5), fmt(5, unit))",
  "answer": "5s 5ms",
  "explanation": "The default was evaluated when def ran, while unit was still \"s\". The second call passes the current value of unit explicitly." }
```

## 3. `*args` and `**kwargs`: collect in a def, unpack in a call

Go's variadic `func total(prices ...int)` collects extra arguments into a slice. Python's `*name` does the same and collects them into a **tuple**. `**name` collects the extra **keyword** arguments into a **dict**, which Go has no equivalent for.

```python
def total(*prices):
    print(type(prices).__name__, prices)
    return sum(prices)

print(total(3, 4, 5))
print(total())

def tag(name, **attrs):
    print(attrs)
    return name

tag("a", href="/home", title="Home")
```

```console
tuple (3, 4, 5)
12
tuple ()
0
{'href': '/home', 'title': 'Home'}
```

In a **call**, the same symbols do the opposite: they **unpack**. `*` spreads a list or tuple into positional arguments (like Go's `total(cart...)`), and `**` spreads a dict into keyword arguments:

```python
cart = [10, 20]
print(total(*cart))        # same as total(10, 20)
opts = {"id": "main"}
tag("div", **opts)         # same as tag("div", id="main")
```

```console
tuple (10, 20)
30
{'id': 'main'}
```

The names `args` and `kwargs` are only a convention. It's the `*` and `**` that do the work.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "def f(a, b=2, *rest, **kw):\n    print(a, b, rest, kw)\n\nf(1, 3, 4, 5, d=7)",
  "answer": "1 3 (4, 5) {'d': 7}",
  "explanation": "1 and 3 fill a and b by position. The leftover positional arguments 4 and 5 go into the tuple rest, and the unknown keyword d=7 goes into the dict kw." }
```

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "`point = {\"x\": 1, \"y\": 2}`. Which call is the same as `move(x=1, y=2)`?",
  "options": ["move(*point)", "move(**point)", "move(point)", "move(point.items())"], "answer": 1,
  "explanation": "** unpacks a dict into keyword arguments. *point would iterate the dict and pass its keys as positional arguments, so move(\"x\", \"y\")." }
```

## 4. Keyword-only and positional-only parameters

Here's a bug Go can't stop at compile time: `Transfer(100, "bob", "alice")` when you meant alice → bob. Both are strings, so the call compiles. Python lets you **require names**: every parameter after a bare `*` (or after `*args`) is **keyword-only**:

```python
def transfer(amount, *, source, target):
    return f"{amount} from {source} to {target}"

print(transfer(100, source="alice", target="bob"))
transfer(100, "alice", "bob")
```

```console
100 from alice to bob
TypeError: transfer() takes 1 positional argument but 3 were given
```

The reverse also exists: parameters **before** a `/` are **positional-only**, so callers can't depend on their names. That lets you rename them later without breaking anyone:

```python
def area(width, height, /):
    return width * height

area(3, 4)                  # 12
area(width=3, height=4)     # TypeError: area() got some positional-only arguments passed as keyword arguments: 'width, height'
```

The full order in a `def`: **positional-only, `/`, normal, `*args` or bare `*`, keyword-only, `**kwargs`.**

```quiz
{ "id": "q6", "type": "truefalse",
  "prompt": "In `def log(msg, *parts, level=\"info\")`, the call `log(\"a\", \"b\", \"warn\")` sets level to \"warn\".", "answer": false,
  "explanation": "level comes after *parts, so it's keyword-only. \"b\" and \"warn\" both go into parts, and level keeps its default \"info\". This silent absorption is why keyword-only parameters should have names that callers will actually write." }
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "A repository function is `def move_item(item_id, from_list_id, to_list_id)`, and all three are ints. Someone called it with the two list ids swapped, and nothing failed. How would you change the signature, and what does it buy you?",
  "model": "Make the list ids keyword-only: def move_item(item_id, *, from_list_id, to_list_id). Every call then has to name them, as in move_item(7, from_list_id=1, to_list_id=2), so a swap is visible in review, and a positional call fails immediately with TypeError instead of moving data to the wrong place.",
  "explanation": "When several arguments share a type, names are the only thing that tells them apart." }
```

## 5. Common mistakes

- **A mutable default (`=[]`, `={}`)**: use `None` (section 2, PY.M02.L04).
- **Checking `if not timeout:` when `0` is a legal value.** Use `if timeout is None:`.
- **Writing manual checks for things the signature already enforces** (`if len(args) < 1: raise ...`). Let Python raise the `TypeError`.
- **Overusing `**kwargs`:** a typo like `timout=3` gets silently collected instead of raising `TypeError`. Use explicit parameters when you know the names. Keep `**kwargs` for open-ended data (like log fields) or for passing arguments through to another function.

## 6. Your turn: design a signature

```exercise
PY.M04.L01.E1
```
