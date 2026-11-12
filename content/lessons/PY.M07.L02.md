---
{
  "id": "PY.M07.L02",
  "title": "Context managers vs Go defer",
  "difficulty": "intermediate",
  "minutes": 45,
  "prerequisites": ["PY.M04.L02", "PY.M07.L01"],
  "objectives": [
    "Use with to guarantee cleanup and explain how it differs from Go's defer (block scope vs function scope)",
    "Predict the order of enter, body, exit and exception handling for a with statement",
    "Write a context manager both as a class (__enter__/__exit__) and with @contextmanager and try/finally",
    "Spot a context manager that skips cleanup or swallows an exception"
  ],
  "why": "Every resource you'll touch as a backend developer needs reliable cleanup: files, DB connections, transactions, locks, temporary settings in tests. In Go you write defer; in Python you write with. Getting the exception path wrong leaks connections or silently hides errors, which are both bugs that only show up under load.",
  "applications": [
    "Opening files and DB connections that are always closed",
    "Transactions that commit on success and roll back on error (DB.M03, SQLAlchemy sessions later)",
    "Temporarily overriding settings or environment in tests and restoring them"
  ],
  "exercises": ["PY.M07.L02.E1"],
  "sources": [
    {
      "title": "The Python Language Reference: 8.5 The with statement; 8.4.4 finally clause",
      "url": "https://docs.python.org/3.12/reference/compound_stmts.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["with is equivalent to calling __enter__, running the body in try, and calling __exit__ with the exception info or with None", "If __exit__ returns a false value the exception is re-raised", "with A() as a, B() as b is the same as nested with statements", "finally always runs; a saved exception is re-raised at the end of finally"]
    },
    {
      "title": "contextlib: Utilities for with-statement contexts",
      "url": "https://docs.python.org/3.12/library/contextlib.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["@contextmanager turns a generator that yields exactly one value into a context manager", "An exception in the with block is reraised inside the generator at the yield, so use try/finally for cleanup", "A generator that catches the exception without re-raising suppresses it", "closing(), suppress() and ExitStack exist for common cases"]
    },
    {
      "title": "Glossary: context manager",
      "url": "https://docs.python.org/3.12/glossary.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["A context manager controls the environment of a with statement by defining __enter__() and __exit__()"]
    },
    {
      "title": "The Go Programming Language Specification: Defer statements",
      "url": "https://go.dev/ref/spec",
      "version": "Go spec (current); Go code in this lesson run with go1.21.0",
      "verified": "2026-11-12",
      "claims": ["Deferred functions run when the surrounding function returns, reaches its end, or its goroutine is panicking", "Deferred calls run in reverse order", "Arguments of a deferred call are evaluated when the defer statement executes"]
    }
  ]
}
---
## 1. Same goal, different scope

In Go you write this every day:

```go
f, err := os.Open(path)
if err != nil {
    return err
}
defer f.Close()
```

The Python equivalent is the `with` statement:

```python
def first_line(path):
    with open(path) as f:
        line = f.readline()
        print("inside:", f.closed)
    print("after the block:", f.closed)
    return line.strip()


print(first_line("app.cfg"))
try:
    with open("app.cfg") as f:
        raise ValueError("bad config")
except ValueError as e:
    print("caught:", e, "| closed:", f.closed)
```

```console
inside: False
after the block: True
host=db1
caught: bad config | closed: True
```

Both guarantee cleanup on every path, including errors. But there is one big difference:

- **Go's `defer` is function-scoped.** The deferred call runs when the *surrounding function* returns (or panics), and multiple defers run in reverse order.
- **Python's `with` is block-scoped.** Cleanup runs the moment the *indented block* ends, even in the middle of a function.

The difference matters most in loops. In Go, a defer inside a loop waits for the whole function to end (run with Go 1.21):

```go
func process(names []string) {
	for _, n := range names {
		fmt.Println("open", n)
		defer fmt.Println("close", n)
	}
	fmt.Println("loop done")
}
```

```console
open a.log
open b.log
loop done
close b.log
close a.log
```

With 10,000 files, that's 10,000 open files at once. The Python version closes each file at the end of its iteration:

```python
for name in ["a", "b"]:
    with open("app.cfg") as f:
        print(name, "open:", not f.closed)
    print(name, "closed:", f.closed)
```

```console
a open: True
a closed: True
b open: True
b closed: True
```

Like `defer` during a panic, `with` does **not stop an exception**: cleanup runs, then the exception keeps travelling up to whoever catches it.

```quiz
{ "id": "q1", "type": "truefalse",
  "prompt": "Like Go's defer, the cleanup of a `with` block runs when the enclosing function returns.", "answer": false,
  "explanation": "with is block-scoped: cleanup runs as soon as the indented block is left (normally, by return/break, or by an exception). defer waits for the surrounding function to return." }
```

## 2. What `with` calls: `__enter__` and `__exit__`

A **context manager** is any object with two methods. `with EXPR as name:` does this:

1. Calls `EXPR.__enter__()` and binds its return value to `name`.
2. Runs the block inside a `try`.
3. Calls `__exit__(exc_type, exc, traceback)` when the block ends: three `None`s if there was no error, or the exception's details if there was.
4. If `__exit__` returns a false value (like `None` or `False`), the exception is re-raised. A true value would **suppress** it, which you almost never want.

```python
class Section:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        print(f"enter {self.name}")
        return self.name.upper()

    def __exit__(self, exc_type, exc, tb):
        print(f"exit {self.name}: {exc_type.__name__ if exc_type else 'no error'}")
        return False      # don't suppress the exception


with Section("load") as label:
    print("body got", label)

try:
    with Section("save"):
        print("saving")
        raise KeyError("disk")
        print("never printed")
except KeyError:
    print("caller sees the KeyError")
```

```console
enter load
body got LOAD
exit load: no error
enter save
saving
exit save: KeyError
caller sees the KeyError
```

Note that `as label` receives what `__enter__` **returns**, not the `Section` object. `open()` returns the file from `__enter__`, which is why `with open(p) as f` gives you the file.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "class Tag:\n    def __enter__(self):\n        print(\"enter\")\n        return self\n\n    def __exit__(self, exc_type, exc, tb):\n        print(\"exit\", exc_type.__name__)\n        return False\n\ntry:\n    with Tag():\n        print(\"body\")\n        1 / 0\nexcept ZeroDivisionError:\n    print(\"caught\")",
  "answer": "enter\nbody\nexit ZeroDivisionError\ncaught",
  "explanation": "__exit__ runs first, with the exception's type, while the exception is still on its way out. It returns False, so the exception continues to the except clause outside." }
```

## 3. `@contextmanager`: a generator with one `yield`

Writing a class for every resource is verbose. `contextlib.contextmanager` turns a generator function (L01) into a context manager:

- the code **before** `yield` is the enter step,
- the **yielded value** is what `as` receives,
- the code **after** `yield` is the exit step.

The crucial rule: if the `with` block raises, the exception is **re-raised inside your generator, at the `yield`**. So cleanup that should always happen must be in a `finally`. Here is a helper that temporarily overrides a setting, the kind of thing you'd use in tests:

```python
from contextlib import contextmanager

MISSING = object()   # a unique marker: "the key wasn't there"


@contextmanager
def override(settings, key, value):
    old = settings.get(key, MISSING)
    settings[key] = value            # runs on enter
    try:
        yield settings               # the with block runs here
    finally:
        if old is MISSING:           # runs on exit, error or not
            del settings[key]
        else:
            settings[key] = old


settings = {"debug": False}
with override(settings, "debug", True):
    print("inside:", settings)
print("after:", settings)

try:
    with override(settings, "timeout", 5):
        print("inside:", settings)
        raise TimeoutError("slow upstream")
except TimeoutError as e:
    print("caught:", e)
print("after error:", settings)
```

```console
inside: {'debug': True}
after: {'debug': False}
inside: {'debug': False, 'timeout': 5}
caught: slow upstream
after error: {'debug': False}
```

Two details worth copying:

- The setup (reading `old`, setting the new value) is **before** the `try`. Only once the resource is really acquired do you promise to release it.
- `MISSING = object()` is a sentinel: it can't be confused with a real value such as `None`, and `is` checks identity (PY.M02).

Without the `finally`, the exception jumps out at the `yield` and the restore line never runs:

```python
@contextmanager
def override(settings, key, value):
    old = settings[key]
    settings[key] = value
    yield settings
    settings[key] = old          # skipped if the block raises!


settings = {"debug": False}
try:
    with override(settings, "debug", True):
        raise RuntimeError("boom")
except RuntimeError:
    pass
print(settings)
```

```console
{'debug': True}
```

In a test suite, that leaked setting breaks a *different* test later, which is a very confusing failure to debug.

```quiz
{ "id": "q3", "type": "choice", "label": "Debugging",
  "prompt": "A `@contextmanager` generator does `lock.acquire()`, `yield`, `lock.release()` with no try/finally. The with block sometimes raises. What happens then?",
  "options": ["The lock is never released, so the next acquire blocks forever", "Python releases the lock automatically at the end of the with block", "The exception is swallowed and the lock is released", "The generator runs the code after yield first, then raises"], "answer": 0,
  "explanation": "The exception is re-raised at the yield, so the line after it is skipped. Only a finally (or except + re-raise) around the yield runs on the error path." }
```

## 4. Don't swallow exceptions by accident

If your generator *catches* the exception and doesn't re-raise it, `@contextmanager` tells `with` the exception was handled. Execution continues after the `with` block as if nothing happened:

```python
from contextlib import contextmanager


@contextmanager
def logged(name):
    try:
        yield
    except Exception as e:
        print(f"{name} failed: {e!r}")      # logged... and swallowed


with logged("charge"):
    raise ValueError("card declined")
print("program continues as if the charge succeeded")
```

```console
charge failed: ValueError('card declined')
program continues as if the charge succeeded
```

If you catch only to log or roll back, end the `except` with a bare `raise` to re-raise the same exception. Suppress on purpose only, and only specific exceptions. The standard library has `contextlib.suppress(FileNotFoundError)` for exactly that, so the intent is visible.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "from contextlib import contextmanager\n\n@contextmanager\ndef quiet():\n    try:\n        yield\n    except KeyError:\n        print(\"ignored\")\n\nwith quiet():\n    {}[\"x\"]\n    print(\"after lookup\")\nprint(\"after with\")",
  "answer": "ignored\nafter with",
  "explanation": "The KeyError leaves the block immediately, so 'after lookup' never runs. The generator catches it without re-raising, which suppresses it, and execution continues after the with statement." }
```

## 5. Several resources: reverse order, like defer

`with A() as a, B() as b:` is the same as nesting the two `with` statements, so exits run in **reverse order**, just like multiple `defer`s:

```python
class Res:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        print("open", self.name)
        return self

    def __exit__(self, *exc):
        print("close", self.name)


with Res("db") as db, Res("cache") as cache:
    print("work")
```

```console
open db
open cache
work
close cache
close db
```

If `cache` fails to open, `db` is still closed, because the outer `with` was already entered. When the number of resources is only known at runtime, `contextlib.ExitStack` combines them. For objects that have a `close()` method but aren't context managers, `contextlib.closing(obj)` wraps them.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "from contextlib import contextmanager\n\n@contextmanager\ndef step(name):\n    print(\"begin\", name)\n    try:\n        yield\n    finally:\n        print(\"end\", name)\n\nwith step(\"tx\"), step(\"lock\"):\n    print(\"work\")",
  "answer": "begin tx\nbegin lock\nwork\nend lock\nend tx",
  "explanation": "Two items in one with statement behave like nested with statements: entered left to right, exited right to left." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "A Go teammate ports `for _, p := range paths { f, _ := os.Open(p); defer f.Close(); ... }` to Python as a for loop with `f = open(p)` and no close, saying 'the garbage collector will close it'. What do you suggest, and how does the Python version behave differently from the Go one?",
  "model": "Use `with open(p) as f:` inside the loop. The file is closed at the end of each iteration, even if an exception is raised, instead of relying on the garbage collector. Unlike the Go version, where every defer waits until the function returns (all files stay open until then), with is block-scoped, so at most one file is open at a time.",
  "explanation": "Block-scoped cleanup is the main practical difference between with and defer." }
```

## 6. Your turn

The exercise is a connection pool: `with pool.lease() as conn:` must always give the connection back, must let exceptions through, and must not corrupt the pool when it's empty. Think about which lines go before the `try` (section 3).

```exercise
PY.M07.L02.E1
```
