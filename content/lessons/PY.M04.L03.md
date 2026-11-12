---
{
  "id": "PY.M04.L03",
  "title": "Designing error handling",
  "difficulty": "intermediate",
  "minutes": 45,
  "prerequisites": ["PY.M04.L02"],
  "objectives": [
    "Spot swallowed errors (bare except, except Exception: pass, returning None) and explain what they hide",
    "Catch narrowly: the right exception class, around the smallest block of code",
    "Decide where an error should be raised, wrapped, and finally handled (at the boundary that can decide a policy)",
    "Choose between EAFP and LBYL for a given situation and justify the choice"
  ],
  "why": "Knowing the syntax isn't the hard part. The hard part is deciding what to catch, where, and what to do about it. Your own shipped Go code has `authors, _ := ...`: an error thrown away, so the program carries on with incomplete data and nobody finds out. Python makes the same mistake one line long (`except: pass`). This lesson is about designing error handling so failures are either handled on purpose or loud.",
  "applications": [
    "Import and ETL jobs that skip bad records, count them and report them, and still crash on real bugs",
    "API handlers that turn domain errors into 404 or 409 responses at one place, the boundary",
    "CLIs that turn exceptions into an error message and an exit code in main(), not deep inside the logic"
  ],
  "exercises": ["PY.M04.L03.E1"],
  "sources": [
    {
      "title": "The Python Tutorial, 8. Errors and Exceptions",
      "url": "https://docs.python.org/3.12/tutorial/errors.html",
      "version": "Python 3.12 docs; examples run with Python 3.12.3",
      "verified": "2026-11-12",
      "claims": [
        "Be as specific as possible about the exception types you handle, and let unexpected exceptions propagate",
        "The most common pattern for handling Exception is to log it and re-raise, so a caller can handle it too",
        "A bare raise re-raises the exception being handled",
        "Use else instead of adding code to try, to avoid catching exceptions from code you didn't mean to protect"
      ]
    },
    {
      "title": "Built-in Exceptions",
      "url": "https://docs.python.org/3.12/library/exceptions.html",
      "version": "Python 3.12 docs",
      "verified": "2026-11-12",
      "claims": [
        "KeyboardInterrupt and SystemExit inherit from BaseException so that code catching Exception doesn't catch them accidentally"
      ]
    },
    {
      "title": "Python Glossary: EAFP and LBYL",
      "url": "https://docs.python.org/3.12/glossary.html",
      "version": "Python 3.12 docs",
      "verified": "2026-11-12",
      "claims": [
        "EAFP assumes valid keys or attributes and catches exceptions if the assumption is false; it is a common Python style",
        "LBYL tests preconditions before calls or lookups; in multi-threaded code it can race between the look and the leap"
      ]
    }
  ]
}
---
## 1. The swallowed error

```python
def average(values):
    try:
        return sum(values) / len(valeus)   # typo
    except:
        return 0

print(average([1, 2, 3]))
```

```console
0
```

The author wanted to handle an empty list. The bare `except:` also caught the `NameError` from the typo, so the function is broken for **every** input, and it says nothing. With `except ZeroDivisionError:` the typo would fail on the first run: `NameError: name 'valeus' is not defined. Did you mean: 'values'?`

It's the same mistake as this Go line:

```go
authors, _ := repo.ListAuthors(ctx)   // error discarded: carries on with nil/partial data
```

Both say: *"if anything goes wrong, pretend it didn't."* There are three Python forms of it, from worst to merely bad:

- **`except:`** catches everything, even `KeyboardInterrupt` (Ctrl-C) and `SystemExit`.
- **`except Exception:` followed by `pass` or `return None`** still hides every bug: `NameError`, `TypeError`, `AttributeError`...
- **Catching the right exception and then returning `None`** loses *why* it failed, and every caller now has to remember to check for `None`. That's an `if err != nil` the compiler doesn't enforce.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "def first_word(text):\n    try:\n        return text.split()[0]\n    except Exception:\n        return \"\"\n\nprint(repr(first_word(\"\")), repr(first_word(None)))",
  "answer": "'' ''",
  "explanation": "The IndexError for an empty string was the case the author meant to handle. The AttributeError from None (a caller bug) is swallowed too, and looks exactly the same. except IndexError would let the None bug surface." }
```

## 2. Catch narrowly: the right class, the smallest block

Two separate rules:

1. **The class:** catch the exception you expect and know how to handle. Everything else must propagate.
2. **The block:** keep `try` to the one call that can raise it. Put the success path in `else`, or after the `try` statement.

```python
# too wide: a KeyError from the parse step would also say "missing setting"
try:
    raw = settings["timeout"]
    timeout = parse_seconds(raw)
except KeyError:
    timeout = 30

# narrow: only the lookup is guarded
try:
    raw = settings["timeout"]
except KeyError:
    timeout = 30
else:
    timeout = parse_seconds(raw)
```

When you need to *see* an unexpected error (to log it) but can't handle it, the tutorial's pattern is **log and re-raise** with a bare `raise`:

```python
try:
    sync_inventory()
except Exception as exc:
    log.error("inventory sync failed: %r", exc)
    raise                      # same exception, same traceback, continues upward
```

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "Which handler is designed best for 'a price field may be missing from a product dict'?",
  "options": [
    "try: price = product[\"price\"] / except KeyError: price = None",
    "try: price = product[\"price\"]; total = price * qty; save(total) / except Exception: pass",
    "try: price = product[\"price\"] / except: price = 0",
    "try: price = product[\"price\"] / except LookupError as e: print(e)"
  ], "answer": 0,
  "explanation": "It catches the one exception that means 'missing', around the one line that can raise it, and makes the outcome explicit. Option 2 hides bugs in save(). Option 3 also catches Ctrl-C and invents a price of 0. Option 4 prints and then carries on without a price, so the next line fails with a NameError." }
```

## 3. Where to handle: raise low, decide at the boundary

The same layering you use in Go applies:

- **Low-level functions** (parse one record, query one row) **raise** a precise error, with context in the message: which line, which id. They can't know the policy, so they don't decide it.
- **Middle layers** either do nothing, so the error propagates (Go's `return err`), or **wrap** it with `raise ... from err` when they add meaning (Go's `%w`).
- **The boundary** (a CLI's `main()`, an HTTP handler, the loop of a batch job) **decides the policy**: skip and count, retry, return a 404, print a message and exit with code 1.

```python
def main(argv):
    try:
        report = build_report(argv[1])
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1                     # an input problem, so exit code 1
    print(report)
    return 0
```

`build_report` and everything it calls contain no `try` for `FileNotFoundError`. Only the layer that knows "this is a CLI" turns it into an exit code. A bug (a `TypeError` somewhere inside) still crashes with a full traceback, which is what you want during development.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "`except Exception:` also catches KeyboardInterrupt, so pressing Ctrl-C inside such a try block is swallowed.", "answer": false,
  "explanation": "KeyboardInterrupt and SystemExit inherit from BaseException, not Exception, precisely so that `except Exception` doesn't trap them. A bare `except:` does catch them." }
```

## 4. EAFP vs LBYL

The glossary names two styles:

- **LBYL**, "look before you leap": check first (`if key in d:`, `if os.path.exists(p):`). This is the usual Go and C style.
- **EAFP**, "easier to ask forgiveness than permission": just do it, and catch the failure (`try: d[key] / except KeyError:`). This is common in Python.

```python
# LBYL: two steps, and something can change in between
if os.path.exists(path):
    with open(path) as f:      # the file may have been deleted between the check and the open
        data = f.read()

# EAFP: one step, no gap
try:
    with open(path) as f:
        data = f.read()
except FileNotFoundError:
    data = ""
```

How to choose:

- **The world can change between the check and the use** (files, other processes or threads, a database row): use **EAFP**. The check would only be a guess.
- **A cheap check on your own data, especially before a side effect** (validate the whole input before writing anything): use **LBYL**. It's clearer, and there's often no specific exception to catch: an empty name isn't an exception at all.
- **Often the best option is neither: use an API that can't fail.** `prices.get("coffee", 0)` instead of `if`/`in` or `try`/`KeyError`.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "Why is `if os.path.exists(p): open(p)` unreliable in a server?",
  "options": ["Another process can delete or replace the file between the check and the open", "os.path.exists is slow", "open() doesn't raise if the file is missing", "exists() returns True for directories only"], "answer": 0,
  "explanation": "That's the race between 'the looking' and 'the leaping'. open() can still raise FileNotFoundError, so you need the except anyway, and then the check adds nothing." }
```

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "stock = {\"tea\": 3}\nmissing = 0\nfor item in [\"tea\", \"coffee\", \"tea\"]:\n    try:\n        count = stock[item]\n    except KeyError:\n        missing += 1\n    else:\n        print(item, count)\nprint(\"missing:\", missing)",
  "answer": "tea 3\ntea 3\nmissing: 1",
  "explanation": "EAFP inside a loop: the missing key is counted and the loop continues. else runs only for successful lookups. This is the shape of 'skip and count' that the exercise asks for." }
```

## 5. A function's error contract

When you design a function, decide its failures like you'd decide its return type:

- **"Not found" is often a normal result, not an error.** `dict.get` returns `None`, while `d[key]` raises. Offer the one that fits how callers use it, and document it.
- **Raise for anything the caller asked for and can't have:** invalid input, a broken invariant, an unreachable dependency. Put the useful facts in the message: the line number, the id, the offending value with `!r`.
- **Give a module one base exception** (`class LoadError(Exception)`) **plus a few subclasses** where callers need to tell cases apart. Callers can then catch everything from your module with one clause. Don't reuse built-in names such as `ImportError` for your own classes.
- **Never `return -1` or `return None` to mean "error"** when the caller can't tell it apart from a real value.

```quiz
{ "id": "q6", "type": "explain", "label": "Debugging",
  "prompt": "Review this code: `def load_users(path):` / `try:` / `rows = read_csv(path); return [User(r) for r in rows]` / `except Exception:` / `return []`. What can go wrong in production, and how would you fix it?",
  "model": "It returns an empty list for a missing file, a permission problem, a malformed row and a bug in User() alike, so the caller can't tell 'no users' from 'something broke', and bugs are hidden. Fix: catch only what this layer can handle (or nothing at all), wrap with a domain error that carries context (raise LoadError(f\"{path}: ...\") from err), and let unexpected exceptions propagate to the boundary. That boundary decides whether to report, skip or exit.",
  "explanation": "An empty list is a value. Using it to mean 'error' is the Python version of `users, _ :=`." }
```

## 6. Your turn: stop swallowing errors

```exercise
PY.M04.L03.E1
```
