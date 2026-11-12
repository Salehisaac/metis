---
{ "id": "PY.M04.A", "module": "PY.M04", "title": "PY.M04 module assessment: functions, errors, writing tests", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before PRJ-01.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?",
  "code": "def f(a, *rest, b=2, **kw):\n    print(a, rest, b, kw)\n\nf(1, 2, 3, c=4)",
  "answer": "1 (2, 3) 2 {'c': 4}",
  "explanation": "1 fills a. 2 and 3 are extra positional arguments, so they go into the tuple rest. b comes after *rest, so it's keyword-only and keeps its default. c=4 isn't a parameter, so it goes into the dict kw." }
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "What does this print?",
  "code": "def load(raw, default=0):\n    try:\n        n = int(raw)\n    except ValueError:\n        print(\"bad\")\n        return default\n    else:\n        print(\"ok\")\n        return n\n    finally:\n        print(\"close\")\n\nprint(load(\"x\"))",
  "answer": "bad\nclose\n0",
  "explanation": "int(\"x\") raises, so except runs and returns the default, 0. finally still runs before the function actually returns, like defer. Only then does print show the returned value." }
```

```quiz
{ "id": "a3", "type": "choice",
  "prompt": "Go: `return fmt.Errorf(\"load user %d: %w\", id, err)`. What's the closest Python, inside `except KeyError as err:`?",
  "options": [
    "raise UserNotFound(f\"load user {id}\") from err",
    "return UserNotFound(f\"load user {id}\"), err",
    "print(f\"load user {id}: {err}\"); return None",
    "raise UserNotFound(f\"load user {id}: {err}\") from None"
  ], "answer": 0,
  "explanation": "from err keeps the original as __cause__, like %w keeps it for errors.Unwrap. Returning the exception doesn't raise it. Printing and returning None swallows the error. from None deliberately hides the cause." }
```

```quiz
{ "id": "a4", "type": "output",
  "prompt": "What does this print?",
  "code": "class AppError(Exception):\n    pass\n\nclass NotFound(AppError):\n    pass\n\nfor exc in (NotFound(\"n\"), AppError(\"a\"), KeyError(\"k\")):\n    try:\n        raise exc\n    except NotFound:\n        print(\"not found\")\n    except AppError:\n        print(\"app\")\n    except LookupError:\n        print(\"lookup\")",
  "answer": "not found\napp\nlookup",
  "explanation": "Each exception goes to the first clause that names its class or a base class. An AppError is not a NotFound, so it falls to the second clause. KeyError is a LookupError." }
```

```quiz
{ "id": "a5", "type": "choice",
  "prompt": "Spec: `discount(total)` gives 10% off for totals of 100 or more, otherwise 0. Which parametrize table catches the bug `if total > 100:`?",
  "options": [
    "[(50, 0), (150, 15)]",
    "[(99, 0), (100, 10), (200, 20)]",
    "[(0, 0), (1000, 100)]",
    "[(150, 15)] plus a pytest.raises test for -1"
  ], "answer": 1,
  "explanation": "Only the boundary row (100, 10) separates > from >=. Tables built from 'typical' values pass on the buggy version." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Debugging",
  "prompt": "A batch job reads orders with `try: order = parse(line); save(order) except Exception: continue`. The report says 0 errors, but the database is missing orders. Explain what's probably happening, and how you would restructure the code and prove it with a test.",
  "model": "except Exception swallows everything: real parse failures, and also bugs or database errors in save(), so orders vanish silently. Restructure: put only parse() in try, catch only the parser's own error (for example a BadOrder subclass of ValueError), count or log those, and call save() in else or after the try, so its errors propagate. Test: a parametrize table of malformed lines that must be counted, plus a test where save raises (or a None line is passed) and pytest.raises asserts that the error is not swallowed.",
  "explanation": "Narrow class, narrow block, and a test that proves the bug can no longer hide." }
```
