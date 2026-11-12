---
{
  "id": "PY.M07.L04",
  "title": "yield-managed resources (FastAPI dependency preview)",
  "difficulty": "intermediate",
  "minutes": 40,
  "prerequisites": ["PY.M07.L01", "PY.M07.L02"],
  "objectives": [
    "Write a resource-providing generator with setup before a single yield and teardown in finally",
    "Drive such a generator by hand the way a framework does: next() for setup, then next(), throw() or close() for teardown",
    "Predict which code runs on success, on an error thrown in at the yield, and on close()",
    "Explain how FastAPI's dependencies with yield relate to contextlib.contextmanager, citing only what its docs state"
  ],
  "why": "In FastAPI you'll write `def get_db(): ... yield db ... finally: db.close()` in almost every project, and the framework runs it for you around each request. If you know what the framework does with your generator, you can predict when the commit, the rollback and the close happen, and you won't write a dependency that leaks connections or silently eats errors.",
  "applications": [
    "Request-scoped database sessions in FastAPI (WEB.M03, WEB.M05)",
    "Per-request resources: HTTP clients, temporary files, locks, tracing spans",
    "Any setup/teardown pair you want to reuse across many handlers or tests"
  ],
  "exercises": ["PY.M07.L04.E1"],
  "sources": [
    {
      "title": "FastAPI docs: Dependencies with yield",
      "url": "https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/",
      "version": "FastAPI docs (page states no version; FastAPI is not installed here, nothing in this lesson runs FastAPI)",
      "verified": "2026-11-12",
      "claims": ["Use yield instead of return and write the extra steps after it", "Use yield one single time per dependency", "Code up to and including yield runs before the response is created; the yielded value is injected; code after yield runs after the response", "Any function valid for @contextlib.contextmanager or @contextlib.asynccontextmanager is a valid dependency; FastAPI uses them internally", "Exceptions raised in the path operation are passed to dependencies with yield; use try/finally for exit steps", "If you catch an exception in such a dependency you should re-raise it; otherwise the server has no log of the error"]
    },
    {
      "title": "FastAPI docs: Dependencies",
      "url": "https://fastapi.tiangolo.com/tutorial/dependencies/",
      "version": "FastAPI docs (page states no version; FastAPI is not installed here)",
      "verified": "2026-11-12",
      "claims": ["A path operation declares a dependency with a parameter like Annotated[..., Depends(func)]", "You pass the function to Depends without calling it", "For each request FastAPI calls the dependency and assigns its result to the parameter"]
    },
    {
      "title": "The Python Language Reference: 6.2.9 Yield expressions (generator.__next__, close, throw)",
      "url": "https://docs.python.org/3.12/reference/expressions.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Calling a generator function returns a generator; execution starts on the first method call and suspends at yield", "throw() raises an exception at the point where the generator is paused", "close() raises GeneratorExit at the paused yield; closing an already closed generator does nothing", "If a generator is not resumed before it is finalized, close() is called so pending finally clauses run"]
    },
    {
      "title": "contextlib: @contextmanager",
      "url": "https://docs.python.org/3.12/library/contextlib.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["The decorated generator must yield exactly one value", "An exception from the with block is reraised inside the generator at the yield", "A generator that catches an exception only to log it must reraise it"]
    }
  ]
}
---
## 1. One function, the whole lifecycle

In L02 you wrote context managers as generators: setup before `yield`, teardown after it, `try/finally` around it. The `with` statement decided when to run each half.

Web frameworks take this one step further: **you write the generator, the framework drives it** around each request. FastAPI calls these *dependencies with yield*. Its docs describe them like this:

- you use `yield` instead of `return`, and write the extra steps after it;
- the code up to and including the `yield` runs **before the response is created**;
- the yielded value is what gets **injected** into your endpoint function;
- the code after the `yield` runs **after the response**;
- use `yield` **only once** per dependency.

Their example is a database session: `db = DBSession()`, then `try: yield db` and `finally: db.close()`. An endpoint asks for it with a parameter such as `db: Annotated[DBSession, Depends(get_db)]`: you pass the function itself to `Depends` without calling it, and for each request FastAPI calls it and assigns the result to that parameter (WEB.M03 covers this properly).

You'll use FastAPI itself from WEB.M01. Everything below is plain Python, so you can run it and see each step without a web server. The Go comparison: in a Go handler you'd write `db := pool.Get(); defer db.Close()` inside each handler, or put it in middleware. Here the setup and teardown live in one reusable function, and the framework calls it for every handler that asks for it.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "In a FastAPI dependency `def get_db(): db = DBSession(); try: yield db; finally: db.close()`, what does the endpoint function receive?",
  "options": ["The db object that was yielded", "The generator object returned by get_db()", "A context manager wrapping db", "None, because get_db has no return statement"], "answer": 0,
  "explanation": "FastAPI's docs: the yielded value is what is injected into path operations and other dependencies. The framework drives the generator; your code only sees the value." }
```

## 2. Driving a dependency by hand

Here is a dependency that gives each request a cache client. Then we play the framework, step by step:

```python
class CacheClient:
    def __init__(self):
        print("  connect")

    def get(self, key):
        return f"value-of-{key}"

    def disconnect(self):
        print("  disconnect")


def get_cache():
    client = CacheClient()        # setup: before the handler runs
    try:
        yield client              # the value the handler receives
    finally:
        client.disconnect()       # teardown: after the handler, always


# What a framework does for one request, by hand:
gen = get_cache()
cache = next(gen)                 # run up to yield, take the value
print("handler:", cache.get("user:7"))
print(next(gen, "teardown done")) # resume after yield: finally runs, then StopIteration
```

```console
  connect
handler: value-of-user:7
  disconnect
teardown done
```

Map it to L01: calling `get_cache()` ran nothing. The first `next()` ran the setup and paused at `yield`. The second `next()` resumed after the `yield`, the `finally` ran, and the generator ended (here `next`'s default value replaced the `StopIteration`).

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "def get_token():\n    print(\"open\")\n    try:\n        yield \"tok\"\n    finally:\n        print(\"close\")\n\ngen = get_token()\nprint(\"request starts\")\ntoken = next(gen)\nprint(\"handler uses\", token)\nprint(next(gen, \"done\"))",
  "answer": "request starts\nopen\nhandler uses tok\nclose\ndone",
  "explanation": "get_token() runs nothing, so 'request starts' is first. The first next() prints 'open' and pauses at yield. The second next() resumes: finally prints 'close', the generator ends, and next returns the default 'done'." }
```

## 3. Two more ways to continue: `throw()` and `close()`

Resuming with `next()` is the success path. A generator has two more methods, and a framework needs both:

- **`gen.throw(exc)`** raises `exc` **at the paused `yield`**. That's how the endpoint's error reaches the dependency: your `except` and `finally` blocks around the `yield` see it.
- **`gen.close()`** raises `GeneratorExit` at the paused `yield`. It's used when nobody will resume the generator. Python also calls `close()` when an unfinished generator is garbage-collected, so pending `finally` blocks still run.

```python
def get_cache():
    print("  connect")
    try:
        yield "client"
    except Exception as e:
        print(f"  dependency saw {e!r}")
        raise                     # let the framework see it too
    finally:
        print("  disconnect")


gen = get_cache()
client = next(gen)
try:
    # the handler failed; the framework hands the error back to the dependency:
    gen.throw(KeyError("user:7"))
except KeyError as e:
    print("framework got:", repr(e))
```

```console
  connect
  dependency saw KeyError('user:7')
  disconnect
framework got: KeyError('user:7')
```

And `close()`:

```python
def get_cache():
    print("  connect")
    try:
        yield "client"
    except GeneratorExit:
        print("  GeneratorExit at the yield")
        raise
    finally:
        print("  disconnect")


gen = get_cache()
next(gen)
gen.close()          # raises GeneratorExit at the paused yield
print("closed")
gen.close()          # closing again does nothing
print("closed twice, no error")
```

```console
  connect
  GeneratorExit at the yield
  disconnect
closed
closed twice, no error
```

One detail that matters for the exercise: `GeneratorExit` is **not** a subclass of `Exception` (it derives from `BaseException`), so `except Exception:` does not catch it, but `finally` still runs.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "def get_conn():\n    try:\n        yield \"conn\"\n    except ValueError:\n        print(\"undo\")\n        raise\n    finally:\n        print(\"release\")\n\ngen = get_conn()\nnext(gen)\ntry:\n    gen.throw(ValueError(\"bad input\"))\nexcept ValueError as e:\n    print(\"framework sees:\", e)",
  "answer": "undo\nrelease\nframework sees: bad input",
  "explanation": "throw() raises the ValueError at the yield. The except block prints 'undo' and re-raises; finally prints 'release'; the re-raised error comes out of throw() to the caller." }
```

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "`except Exception:` around the yield also runs when the framework calls `gen.close()`.", "answer": false,
  "explanation": "close() raises GeneratorExit, which derives from BaseException, not Exception. The except Exception block is skipped; a finally block still runs." }
```

## 4. Under the hood: it's `contextmanager`

FastAPI's docs say that any function that would be valid with `@contextlib.contextmanager` (or `asynccontextmanager`, for async code) is a valid dependency, and that FastAPI uses those decorators internally. So you already know the semantics from L02. A tiny stand-in for a framework, in plain Python:

```python
from contextlib import contextmanager


def get_cache():
    print("  connect")
    try:
        yield {"user:7": "ana"}
    finally:
        print("  disconnect")


def handle(handler):
    """A tiny stand-in for a framework: run one request with one dependency."""
    with contextmanager(get_cache)() as cache:
        return handler(cache)


print(handle(lambda cache: cache["user:7"]))
try:
    handle(lambda cache: cache["user:8"])
except KeyError as e:
    print("500 for this request:", repr(e))
```

```console
  connect
  disconnect
ana
  connect
  disconnect
500 for this request: KeyError('user:8')
```

The `with` statement does the `next()` / `throw()` work from section 3 for you: on success it resumes the generator, on an error it throws the exception in at the `yield`. Note that `get_cache` itself has no decorator. The framework (here `handle`) wraps it, which matches FastAPI's advice not to put the decorators on your dependencies yourself.

```quiz
{ "id": "q7", "type": "output",
  "prompt": "What does this print?",
  "code": "from contextlib import contextmanager\n\ndef get_limit():\n    print(\"setup\")\n    try:\n        yield 5\n    finally:\n        print(\"teardown\")\n\ndef handle(handler):\n    with contextmanager(get_limit)() as limit:\n        return handler(limit)\n\nprint(handle(lambda limit: limit * 2))",
  "answer": "setup\nteardown\n10",
  "explanation": "The handler's result is computed inside the with block, but return leaves the block first, so teardown runs before print receives 10. Same as a Go defer running before the caller gets the return value." }
```

"Use `yield` once" is not just style. `contextmanager` refuses a generator that yields twice:

```python
from contextlib import contextmanager


@contextmanager
def two_values():
    yield "first"
    yield "second"


try:
    with two_values() as v:
        print("got", v)
except RuntimeError as e:
    print("RuntimeError:", e)
```

```console
got first
RuntimeError: generator didn't stop
```

## 5. Don't eat the error

The FastAPI docs are explicit: exceptions raised in your endpoint are passed to dependencies with `yield`, and **if you catch one, you should re-raise it** (or raise another HTTP error on purpose). If you swallow it, the client still gets a 500 Internal Server Error, but the server has **no log** of what went wrong. That's the same rule as L02, section 4, now with production consequences: a silent 500 is very hard to debug. A bare `raise` inside `except` re-raises the same exception with its original traceback, as in section 3.

```quiz
{ "id": "q5", "type": "choice", "label": "Debugging",
  "prompt": "A dependency does `try: yield client` / `except Exception as e: logger.warning(e)` / `finally: client.close()`. Users report occasional 500 errors, but the error logs show nothing useful. Following the FastAPI docs, what's the fix?",
  "options": ["Re-raise in the except block (bare `raise`) after logging", "Remove the finally block", "Yield the client twice, once for errors", "Catch BaseException instead of Exception"], "answer": 0,
  "explanation": "Catching without re-raising swallows the exception, so the framework never sees it and can't log it. Re-raise after your own handling. finally is still needed for close()." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "A Go teammate asks: why does FastAPI want the DB dependency written as a generator with yield, instead of one function that returns the connection plus a separate cleanup function the handler calls at the end?",
  "model": "With yield, setup and teardown live in one function and share local variables. The framework, not each handler, guarantees the teardown runs after the request, also when the handler raises (the error is thrown in at the yield, so the dependency can react to it, and finally always runs). A separate cleanup function relies on every handler remembering to call it on every path, which is the bug defer exists to prevent in Go.",
  "explanation": "The generator is a reusable defer that the framework runs for you." }
```

## 6. Your turn

The exercise is exactly that dependency: `get_session(make_session)`. The tests act as the framework: they call `next()`, `throw()` and `close()` on your generator, and also run it through `contextmanager`. Draw the three paths from section 3 before you write code.

```exercise
PY.M07.L04.E1
```
