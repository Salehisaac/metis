---
{
  "id": "PY.M04.L02",
  "title": "Exceptions vs Go error values",
  "difficulty": "beginner",
  "minutes": 45,
  "prerequisites": ["PY.M04.L01"],
  "objectives": [
    "Map Go's (value, error) return plus if err != nil to Python's raise and try/except",
    "Predict the execution order of try/except/else/finally, and relate finally to defer",
    "Predict which except clause catches an exception, using the class hierarchy",
    "Define a minimal custom exception (hierarchy) and wrap a low-level error with raise ... from err, like %w"
  ],
  "why": "Your assessment flagged exceptions as a gap. In Go every failing call hands you an error value that you must check. Python inverts that: failures travel up the call stack by themselves until someone catches them. Every Python library you'll use (FastAPI, SQLAlchemy, httpx) reports problems this way, so reading and raising exceptions is basic literacy.",
  "applications": [
    "Turning a library's KeyError or ValueError into your own domain error (NotFoundError, InvalidInput)",
    "Cleanup that must always run (closing a file or a connection), like defer",
    "Reading a chained traceback to find the original cause of a failure"
  ],
  "exercises": ["PY.M04.L02.E1"],
  "sources": [
    {
      "title": "The Python Tutorial, 8. Errors and Exceptions",
      "url": "https://docs.python.org/3.12/tutorial/errors.html",
      "version": "Python 3.12 docs; examples run with Python 3.12.3",
      "verified": "2026-11-12",
      "claims": [
        "An except clause matches instances of its class or derived classes; the first matching clause is used",
        "The else clause runs if the try clause raises nothing, and is better than adding code to try because it avoids catching exceptions from code you didn't mean to protect",
        "finally runs whether or not an exception occurred, and is used to release resources",
        "raise ... from exc indicates that an exception is a direct consequence of another; from None disables automatic chaining",
        "An exception raised inside an except clause has the handled exception attached ('During handling of the above exception, another exception occurred')",
        "User-defined exceptions should derive from Exception; most names end in 'Error'"
      ]
    },
    {
      "title": "Built-in Exceptions",
      "url": "https://docs.python.org/3.12/library/exceptions.html",
      "version": "Python 3.12 docs",
      "verified": "2026-11-12",
      "claims": [
        "An except clause naming a class also handles its subclasses, not its base classes",
        "raise new_exc from original_exc sets __cause__; an exception raised while handling another gets __context__ automatically",
        "LookupError is the base class of IndexError and KeyError",
        "User-defined exceptions should derive from Exception, not BaseException"
      ]
    },
    {
      "title": "The Python Language Reference, 8.4 The try statement",
      "url": "https://docs.python.org/3.12/reference/compound_stmts.html#the-try-statement",
      "version": "Python 3.12 docs",
      "verified": "2026-11-12",
      "claims": [
        "except clauses are inspected in turn until one matches (the class, a base class, or a tuple containing one)",
        "A name bound with 'as' is cleared at the end of the except clause",
        "Exceptions raised in the else clause are not handled by the preceding except clauses",
        "The finally clause always executes"
      ]
    }
  ]
}
---
## 1. Same failure, two mechanisms

```go
n, err := strconv.Atoi(s)
if err != nil {
    return 0, fmt.Errorf("parse limit: %w", err)
}
```

In Go the error is a **return value**. You check it on every call, and if you forget, the program carries on with `n == 0`. In Python, a failing call **raises an exception** and returns nothing at all:

```python
int("x")
```

```console
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ValueError: invalid literal for int() with base 10: 'x'
```

An exception that nobody catches unwinds the stack, function by function, until it reaches the top, where Python prints the traceback and exits. That looks like a Go `panic`, but it's **the normal way to report errors** in Python, not a last resort. The consequences:

- **Code in between doesn't need `if err != nil`.** A function that can't handle an error simply doesn't catch it, and it passes upward automatically.
- **You can't forget to check by accident.** An unhandled error stops the program loudly instead of continuing with a zero value.
- **The cost:** a function signature doesn't show what it may raise. You learn that from the docs, the docstring and tests.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "What does `int(\"x\")` return?",
  "options": ["0 and an error value, like strconv.Atoi", "None", "Nothing: it raises ValueError, so there is no return value", "-1"], "answer": 2,
  "explanation": "A Python function either returns a value or raises. There is no (value, error) pair to unpack, and no zero value to use by mistake." }
```

## 2. try / except / else / finally

```python
def run(text):
    try:
        n = int(text)          # only the code that can fail
    except ValueError:
        print("bad")           # runs if try raised ValueError
    else:
        print("ok", n)         # runs if try raised nothing
    finally:
        print("done")          # always runs, like defer

run("7")
run("x")
```

```console
ok 7
done
bad
done
```

Why each part exists:

- **`try`** holds only the call you expect to fail. Everything you add to it is code whose errors you might catch by accident.
- **`except ValueError`** handles that one kind of failure. An `except` without a class catches *everything*, including bugs (more in L03).
- **`else`** is the success path. The tutorial recommends it over putting more code in `try`, because an exception raised in `else` is *not* caught by the `except` above it.
- **`finally`** is Go's `defer`: cleanup that runs whether the block succeeded, failed or returned early. For files and connections you'll usually use `with`, which does this for you.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "def check(d):\n    try:\n        v = d[\"k\"]\n    except KeyError:\n        print(\"missing\")\n        return\n    else:\n        print(\"got\", v)\n    finally:\n        print(\"end\")\n\ncheck({})\ncheck({\"k\": 1})",
  "answer": "missing\nend\ngot 1\nend",
  "explanation": "finally runs even when except returns early, just as defer runs on every return path in Go." }
```

## 3. Which `except` catches it: the hierarchy

Go has `errors.Is` and `errors.As`. Python matches on **classes**: `except C` catches an exception of class `C` **or any subclass of `C`**. The built-in exceptions form a tree (excerpt):

```text
BaseException
 ├── KeyboardInterrupt, SystemExit
 └── Exception
      ├── ArithmeticError → ZeroDivisionError
      ├── LookupError → IndexError, KeyError
      ├── OSError → FileNotFoundError, ...
      └── ValueError → UnicodeError
```

So `except LookupError` catches both a missing dict key and an out-of-range list index. Python tries the `except` clauses **from top to bottom, and the first match wins**, so put the specific classes before the general ones.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "try:\n    {}[\"k\"]\nexcept LookupError as e:\n    print(type(e).__name__, e)",
  "answer": "KeyError 'k'",
  "explanation": "KeyError is a subclass of LookupError, so the clause matches, and e is the actual KeyError. str() of a KeyError is the repr of the key, which is why the quotes appear." }
```

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "`try: [][0]` is followed by `except Exception: print(\"A\")` and then `except IndexError: print(\"B\")`. What prints?",
  "options": ["A", "B", "A then B", "Nothing: it's a SyntaxError"], "answer": 0,
  "explanation": "IndexError is a subclass of Exception, and clauses are tried in order, so the first one wins. The IndexError clause can never run. Put specific classes first." }
```

## 4. Your own exceptions: sentinel errors as classes

In Go you'd write `var ErrNotFound = errors.New("not found")` and check it with `errors.Is`. In Python you define a **class** and catch it by name. A minimal class is enough (classes properly come in PY.M05):

```python
class StoreError(Exception):        # base for everything this module raises
    pass


class NotFoundError(StoreError):    # one specific failure
    pass
```

- **Derive from `Exception`**, never from `BaseException`, which is reserved for things like `KeyboardInterrupt` (Ctrl-C).
- **End the name in `Error`**, following the convention of the built-ins.
- **A small hierarchy gives callers a choice,** the way `errors.Is` works across a wrapped chain: `except NotFoundError` handles one case, and `except StoreError` handles anything from your module.
- **Subclass a built-in when the meaning fits.** `class PriceError(ValueError)` stays catchable by code that already handles `ValueError`.

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "With `class NotFoundError(StoreError)`, the clause `except NotFoundError:` also catches a plain `StoreError(\"disk full\")`.", "answer": false,
  "explanation": "Matching only goes from parent to child: except StoreError catches NotFoundError, but not the other way round. A StoreError is not a NotFoundError." }
```

## 5. Wrapping: `raise ... from err` is `%w`

When a low-level error means something at your level, translate it, and keep the original attached (`users.py` is the two classes from section 4 plus this):

```python
USERS = {1: "ada"}


def get_user(user_id):
    try:
        return USERS[user_id]
    except KeyError as err:
        raise NotFoundError(f"user {user_id}") from err


get_user(3)
```

```console
$ python3 users.py
Traceback (most recent call last):
  ...
KeyError: 3

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  ...
NotFoundError: user 3
```

| Go | Python |
|---|---|
| `fmt.Errorf("user %d: %w", id, err)` | `raise NotFoundError(f"user {id}") from err` |
| `errors.Unwrap(err)` | `e.__cause__` |
| `errors.Is(err, ErrNotFound)` | `except NotFoundError:` / `isinstance(e, NotFoundError)` |
| `var nf *NotFoundError; errors.As(err, &nf)` | `except NotFoundError as e:` (and `e` is typed) |

Without `from`, Python still records the original, but as `__context__`, and the traceback says *"During handling of the above exception, another exception occurred"*. That reads like a second bug in your handler, so use `from err` when the translation is deliberate. `raise ... from None` hides the original when it's pure noise.

One more difference from Go: the name after `as` is deleted when the `except` block ends, so copy it to another variable if you need it later.

```quiz
{ "id": "q6", "type": "output",
  "prompt": "What does this print?",
  "code": "class NotFoundError(Exception):\n    pass\n\ndef find(key):\n    try:\n        return {}[key]\n    except KeyError as err:\n        raise NotFoundError(key) from err\n\ntry:\n    find(\"x\")\nexcept NotFoundError as e:\n    print(e, type(e.__cause__).__name__)",
  "answer": "x KeyError",
  "explanation": "str(e) is the message passed to NotFoundError (\"x\"). __cause__ is the original KeyError, attached by from err, just as %w keeps the wrapped error reachable." }
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "Translate this Go into Python: `cfg, err := loadConfig(path); if err != nil { return fmt.Errorf(\"start server: %w\", err) }`, where loadConfig raises OSError when the file is missing. Assume a ServerError class exists.",
  "model": "try: cfg = load_config(path) / except OSError as err: raise ServerError(\"start server\") from err. Only the load_config call goes inside try, and the code that uses cfg goes after the try statement (or in else). If this layer has nothing to add, write no try at all and let OSError propagate: that is Python's version of returning err unchanged.",
  "explanation": "Wrap when you add meaning; otherwise let it propagate." }
```

## 6. Your turn: translate a Go function

```exercise
PY.M04.L02.E1
```
