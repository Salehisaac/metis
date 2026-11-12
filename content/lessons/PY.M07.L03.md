---
{
  "id": "PY.M07.L03",
  "title": "Closures and decorators",
  "difficulty": "intermediate",
  "minutes": 50,
  "prerequisites": ["PY.M04.L01", "PY.M04.L02", "PY.M07.L02"],
  "objectives": [
    "Explain what a closure captures (the variable, not its value) and use nonlocal to rebind a captured variable",
    "Predict and fix the late-binding bug when functions are created in a loop",
    "Write a decorator as a function that returns a wrapper, preserving metadata with functools.wraps",
    "Write a decorator that takes arguments (three layers) and predict when each layer runs"
  ],
  "why": "Decorators are everywhere in Python backends: route registration, auth checks, caching, retries, timing, transactions. You'll read them in every framework long before you write one, and reading them requires knowing exactly which code runs at definition time and which runs on each call.",
  "applications": [
    "Cross-cutting concerns without copy-paste: timing, logging, retries, permission checks",
    "Registering handlers or plugins when a module is imported",
    "Factory functions that keep private state (counters, caches, configuration)"
  ],
  "exercises": ["PY.M07.L03.E1"],
  "sources": [
    {
      "title": "Python FAQ: Programming (lambdas in a loop; UnboundLocalError; local and global variables)",
      "url": "https://docs.python.org/3.12/faq/programming.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["A function defined in a loop looks up the loop variable when called, not when defined", "A default argument n=x stores the value at definition time", "This applies to regular functions too, not only lambdas", "Assigning to a variable anywhere in a function makes it local; nonlocal allows rebinding a variable of an enclosing function"]
    },
    {
      "title": "Glossary: decorator, nested scope",
      "url": "https://docs.python.org/3.12/glossary.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["A decorator is a function returning another function, applied with @wrapper syntax", "@decorator is syntactic sugar for f = decorator(f)", "Nested scopes work for reference, not assignment, unless nonlocal is used"]
    },
    {
      "title": "The Python Language Reference: 8.7 Function definitions",
      "url": "https://docs.python.org/3.12/reference/compound_stmts.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Decorator expressions are evaluated when the function is defined", "The decorator's result is bound to the function name", "@f1(arg) @f2 def func is roughly func = f1(arg)(f2(func))"]
    },
    {
      "title": "functools: update_wrapper and wraps",
      "url": "https://docs.python.org/3.12/library/functools.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["wraps copies __module__, __name__, __qualname__, __annotations__, __type_params__ and __doc__ to the wrapper", "update_wrapper adds __wrapped__ pointing to the original function", "Without wraps the decorated function's name would be 'wrapper' and its docstring lost"]
    },
    {
      "title": "time: perf_counter",
      "url": "https://docs.python.org/3.12/library/time.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["perf_counter is a high-resolution clock for short durations; only the difference between two calls is meaningful"]
    },
    {
      "title": "Go 1.22 Release Notes",
      "url": "https://go.dev/doc/go1.22",
      "version": "Go 1.22",
      "verified": "2026-11-12",
      "claims": ["Since Go 1.22 each iteration of a for loop creates new loop variables, to avoid accidental sharing bugs"]
    }
  ]
}
---
## 1. Closures: inner functions remember their scope

You know closures from Go: a function literal can use variables of the function around it, and it keeps them alive after that function returns. Python works the same way:

```python
def make_counter():
    count = 0

    def increment():
        nonlocal count      # rebind the outer variable, don't create a local
        count += 1
        return count

    return increment


hits = make_counter()
print(hits(), hits(), hits())
other = make_counter()
print(other())
print(hits.__closure__[0].cell_contents)
```

```console
1 2 3
1
3
```

Each call of `make_counter` creates a new `count`, so `hits` and `other` don't share state. `__closure__` shows where the captured variable lives. You'll never need it in real code, but it proves the variable is stored with the function.

One difference from Go: in Python, **assigning** to a name anywhere in a function makes that name local to the function. Without `nonlocal`, `count += 1` creates a new local `count` and fails, because it reads the local before assigning it:

```python
def make_counter():
    count = 0

    def increment():
        count += 1          # assignment makes count local to increment
        return count

    return increment


try:
    make_counter()()
except UnboundLocalError as e:
    print("UnboundLocalError:", e)
```

```console
UnboundLocalError: cannot access local variable 'count' where it is not associated with a value
```

Reading a captured variable needs nothing. Only *rebinding* it needs `nonlocal`. Mutating a captured list or dict (`items.append(x)`) doesn't rebind, so it doesn't need `nonlocal` either (PY.M02: mutation vs rebinding).

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "def make_tally(start):\n    total = start\n\n    def add(n):\n        nonlocal total\n        total += n\n        return total\n\n    return add\n\na = make_tally(10)\nb = make_tally(0)\nprint(a(5), b(5), a(1))",
  "answer": "15 5 16",
  "explanation": "Each make_tally call creates its own total. a starts at 10: 10+5 = 15, then 15+1 = 16. b has its own total starting at 0, so b(5) is 5." }
```

## 2. The late-binding gotcha in loops

A closure captures the **variable**, not the value it had when the function was created. The value is looked up when the function is **called**. In a loop, every function you create shares the one loop variable, and by the time you call them the loop has finished:

```python
checks = []
for port in [8000, 8001, 8002]:
    checks.append(lambda: f"checking {port}")
print([check() for check in checks])

checks = []
for port in [8000, 8001, 8002]:
    checks.append(lambda port=port: f"checking {port}")   # value bound now
print([check() for check in checks])
```

```console
['checking 8002', 'checking 8002', 'checking 8002']
['checking 8000', 'checking 8001', 'checking 8002']
```

The fix uses a default argument: defaults are evaluated **once, when the function is defined**, so `port=port` stores the current value in the function's own parameter. A factory function (`def make_check(port): return lambda: ...`) works too, because each call creates a new variable.

Go had exactly this bug with goroutines and closures in loops, until **Go 1.22 made each loop iteration create new variables**. If you learned Go on 1.22 or later, you may never have seen it. Python did not make that change: a Python `for` loop has one variable for the whole loop, and it still exists after the loop ends.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "fns = []\nfor i in range(3):\n    def times_ten():\n        return i * 10\n    fns.append(times_ten)\nprint([f() for f in fns])",
  "answer": "[20, 20, 20]",
  "explanation": "It isn't specific to lambdas. All three functions look up i when they're called, after the loop ended with i == 2. Use `def times_ten(i=i):` to bind the value at definition time." }
```

## 3. A decorator is a function that returns a function

Functions are objects: you can pass them as arguments and return them. A **decorator** takes a function and returns a replacement, usually a `wrapper` that does something extra and then calls the original, which it remembers through a closure. `@logged` above a `def` is just shorthand for `add = logged(add)`:

```python
def logged(func):
    print(f"decorating {func.__name__}")

    def wrapper(*args, **kwargs):
        print(f"call {func.__name__}{args}")
        return func(*args, **kwargs)

    return wrapper


@logged                # same as: add = logged(add)
def add(a, b):
    """Return a + b."""
    return a + b


print("defined")
print(add(2, 3))
print(add.__name__, add.__doc__)
```

```console
decorating add
defined
call add(2, 3)
5
wrapper None
```

Read the output carefully:

- **`decorating add` comes before `defined`.** The decorator runs once, when the `def` statement executes (usually at import time), not when you call `add`.
- **The wrapper runs on every call.** `*args, **kwargs` (PY.M04) let it accept any arguments and forward them unchanged.
- **The name `add` now points to `wrapper`.** That's why the last line shows `wrapper None`: the original name and docstring are gone. Section 4 fixes that.

In Go you'd write the same idea as a function that takes a `func` and returns a `func`; HTTP middleware (`func(next http.Handler) http.Handler`) is exactly this pattern. Python only adds the `@` syntax.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "def register(func):\n    print(\"registering\", func.__name__)\n    return func\n\n@register\ndef ping():\n    return \"pong\"\n\nprint(\"start\")\nprint(ping())",
  "answer": "registering ping\nstart\npong",
  "explanation": "The decorator runs when def ping executes, before 'start'. It returns the original function unchanged, so ping() works normally. Decorators like this are how frameworks register handlers when a module is imported." }
```

```quiz
{ "id": "q4", "type": "choice", "label": "Debugging",
  "prompt": "After adding a home-made `@audit` decorator, `total = compute_total(cart)` sets total to None, although compute_total returns a number. The wrapper is: `def wrapper(*args, **kwargs): log(func.__name__); func(*args, **kwargs)`. What's wrong?",
  "options": ["The wrapper calls func but doesn't return its result", "The wrapper should take only *args", "log() replaced the return value", "Decorated functions can't return values"], "answer": 0,
  "explanation": "A Python function without return returns None. The wrapper replaces compute_total, so its return value is what callers get. It must `return func(*args, **kwargs)`." }
```

## 4. `functools.wraps`: keep the original's identity

Losing `__name__` and `__doc__` makes tracebacks, logs and debugging tools show `wrapper` everywhere. `functools.wraps` copies the metadata (`__name__`, `__doc__`, `__qualname__`, `__module__`, annotations) from the original onto the wrapper and stores the original as `__wrapped__`:

```python
from functools import wraps


def logged(func):
    @wraps(func)       # copy __name__, __doc__, ... from func onto wrapper
    def wrapper(*args, **kwargs):
        print(f"call {func.__name__}{args}")
        return func(*args, **kwargs)

    return wrapper


@logged
def add(a, b):
    """Return a + b."""
    return a + b


print(add.__name__, add.__doc__)
print(add.__wrapped__(2, 3))
```

```console
add Return a + b.
5
```

`add.__wrapped__(2, 3)` called the original directly, without the log line. Note that `wraps` is itself a decorator that takes an argument, which is the topic of section 6. Rule: **every wrapper you write gets `@wraps(func)`**.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "def bold(func):\n    def wrapper():\n        return \"<b>\" + func() + \"</b>\"\n    return wrapper\n\ndef italic(func):\n    def wrapper():\n        return \"<i>\" + func() + \"</i>\"\n    return wrapper\n\n@bold\n@italic\ndef hello():\n    return \"hi\"\n\nprint(hello(), hello.__name__)",
  "answer": "<b><i>hi</i></b> wrapper",
  "explanation": "Stacked decorators apply bottom-up: hello = bold(italic(hello)). So bold's wrapper is outermost and its tags end up outside. Neither uses @wraps, so the name is 'wrapper'." }
```

## 5. A practical decorator: timing

Measuring how long a call takes is a classic cross-cutting concern. `time.perf_counter()` is the clock for short durations; only the difference between two readings means anything. The `try/finally` (L02) makes sure the time is printed even if the call raises:

```python
import time
from functools import wraps


def timed(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            print(f"{func.__name__} took {elapsed:.3f}s")

    return wrapper


@timed
def slow_query(n):
    time.sleep(0.2)
    return [n] * 3


print(slow_query(7))
```

```console
slow_query took 0.200s
[7, 7, 7]
```

(Your number will differ slightly.) The `finally` runs *before* the caller receives the return value, so the timing line is printed first.

## 6. Decorators with arguments: three layers

`@timed` takes no settings. To write `@require_role("admin")`, you need one more layer: `require_role("admin")` is called first, and its **result** must be the actual decorator. That gives three nested functions, each with one job:

```python
from functools import wraps


def require_role(role):                 # 1. takes the decorator's argument
    def decorator(func):                # 2. takes the function
        @wraps(func)
        def wrapper(user, *args, **kwargs):   # 3. runs on every call
            if role not in user["roles"]:
                raise PermissionError(f"{user['name']} needs role {role!r}")
            return func(user, *args, **kwargs)

        return wrapper

    return decorator


@require_role("admin")                  # same as: delete_order = require_role("admin")(delete_order)
def delete_order(user, order_id):
    return f"order {order_id} deleted by {user['name']}"


ana = {"name": "ana", "roles": ["admin"]}
bob = {"name": "bob", "roles": ["support"]}
print(delete_order(ana, 42))
try:
    delete_order(bob, 42)
except PermissionError as e:
    print("PermissionError:", e)
```

```console
order 42 deleted by ana
PermissionError: bob needs role 'admin'
```

When each layer runs:

| Layer | Runs | Typical work |
|---|---|---|
| `require_role(role)` | once, at the `@` line | validate the settings |
| `decorator(func)` | once, right after | wrap the function |
| `wrapper(...)` | on every call | the actual behaviour |

`role` is captured by a closure, so every wrapper remembers its own role. The order of evaluation is defined by the language: `@f1(arg)` then `@f2` above `def func` is roughly `func = f1(arg)(f2(func))`.

**Common mistakes:**

- Writing `@require_role` without parentheses. `require_role(delete_order)` then returns `decorator`, so `delete_order` *becomes* `decorator`, and the first call fails confusingly.
- Validating settings inside `wrapper`: a bad setting then fails on the first request in production instead of at import time.
- Keeping per-call state (a counter) in the outer layers: it's created once and shared by every call (section 1).

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "Someone writes `@require_role` (no parentheses) above `def delete_order(user, order_id)`. What does `delete_order(ana, 42)` do?",
  "options": ["Raises TypeError, because delete_order is now the inner `decorator`, which takes one argument", "Works, with role set to None", "Raises PermissionError", "Deletes the order without checking the role"], "answer": 0,
  "explanation": "@require_role means delete_order = require_role(delete_order). That returns the inner decorator function, which takes a single func parameter, so calling it with two arguments raises TypeError." }
```

```quiz
{ "id": "q7", "type": "truefalse",
  "prompt": "In a decorator with arguments, code in the outermost function (the one that receives the arguments) runs every time the decorated function is called.", "answer": false,
  "explanation": "The outer layer runs once, when the @ line is executed. Only the innermost wrapper runs on every call." }
```

## 7. Your turn

The exercise is a `@retry(times, exceptions=...)` decorator, the kind you'd put around a flaky network call. The tests check the edge cases: `times == 1`, an invalid `times`, exceptions that must *not* be retried, keyword arguments, and that every call gets a fresh set of attempts (remember section 1).

```exercise
PY.M07.L03.E1
```
