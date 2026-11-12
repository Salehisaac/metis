---
{
  "id": "PY.M04.L04",
  "title": "Writing your own tests",
  "difficulty": "intermediate",
  "minutes": 50,
  "prerequisites": ["PY.M04.L03", "PY.M01.L03"],
  "objectives": [
    "Turn a written spec into a list of edge cases before writing any code: empty, boundaries, whitespace, invalid input",
    "Write a table-driven test with @pytest.mark.parametrize and read its per-case test ids",
    "Test the error path with pytest.raises(..., match=...), knowing that match uses re.search",
    "Write a test that fails on a seeded bug and passes on the fix, and debug it with pytest -x -vv"
  ],
  "why": "Until now the tests came with the exercise. From here on you write them, starting with PRJ-01, where your tests are 20 of the 100 points. Your assessment showed the pattern this lesson targets: you checked the one given example, and the bug was in the cases you didn't try. Table-driven tests are something you already know from Go. This lesson is about the Python form, and about choosing rows that actually catch bugs.",
  "applications": [
    "A regression test for every bug you fix, written before the fix",
    "Table-driven tests for parsers and validators: many inputs, one assertion",
    "Testing that bad input fails with the right exception and message, not just any exception"
  ],
  "exercises": ["PY.M04.L04.E1"],
  "sources": [
    {
      "title": "How to parametrize fixtures and test functions",
      "url": "https://docs.pytest.org/en/stable/how-to/parametrize.html",
      "version": "pytest stable docs (9.x); verified locally with pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": [
        "@pytest.mark.parametrize parametrizes the arguments of a test function: comma-separated argument names and a list of tuples of values",
        "Each set of values runs as a separate test, shown with an id such as test_eval[6*9-42]",
        "pytest.param can wrap one set of values, for example to mark it",
        "Stacked parametrize decorators produce all combinations"
      ]
    },
    {
      "title": "How to write and report assertions in tests",
      "url": "https://docs.pytest.org/en/stable/how-to/assert.html",
      "version": "pytest stable docs (9.x); verified locally with pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": [
        "pytest.raises is used as a context manager to assert that an exception is raised",
        "excinfo is an ExceptionInfo whose main attributes are .type, .value and .traceback",
        "The match parameter is matched against the string representation of the exception with re.search",
        "pytest.raises also matches subclasses of the given exception type"
      ]
    },
    {
      "title": "API Reference: pytest.raises and pytest.param",
      "url": "https://docs.pytest.org/en/stable/reference/reference.html",
      "version": "pytest stable docs (9.x); verified locally with pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": [
        "If no exception (or a different one) is raised, the pytest.raises check fails",
        "To match a literal string that may contain special characters, escape the pattern with re.escape",
        "The raising call must be the last line in the with block; lines after it are not executed",
        "pytest.raises(Exception) can easily hide real bugs",
        "pytest.param takes the values plus an optional id and marks"
      ]
    },
    {
      "title": "Managing pytest's output",
      "url": "https://docs.pytest.org/en/stable/how-to/output.html",
      "version": "pytest stable docs (9.x); verified locally with pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": ["-v prints one line per test; -vv increases verbosity further and does not truncate diffs"]
    },
    {
      "title": "How to handle test failures",
      "url": "https://docs.pytest.org/en/stable/how-to/failures.html",
      "version": "pytest stable docs (9.x); verified locally with pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": ["pytest -x stops after the first failure; --maxfail=N after N failures"]
    }
  ]
}
---
## 1. Before any test: list the cases

A test can only catch a bug for an input someone thought of. So the first step isn't code. It's a list of inputs, taken from the spec. This checklist covers most of what you'll need:

| Category | Ask yourself | Example for "parse a percentage like `'42%'`" |
|---|---|---|
| Typical | the example from the spec | `'42%'` → 42 |
| Boundaries | both limits, and one past each | `'0%'`, `'100%'`, `'-1%'`, `'101%'` |
| Nothing | empty, blank, zero, empty list | `''`, `'   '` |
| Formatting | whitespace, case, optional parts | `' 42% '`, `'42'` (no `%`) |
| Invalid | wrong type of content | `'abc'`, `'4.5%'` |
| Many / ties | duplicates, equal keys, order | (for sorting and ranking functions) |

Write the list *first*, then the code. The code then has to handle the cases, instead of the cases being chosen to fit the code.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Spec: `is_adult(age)` is True for ages 18 and over. Which set of test inputs would catch the bug `return age > 18`?",
  "options": ["25, 40, 10", "17, 18, 19", "0, 100", "30"], "answer": 1,
  "explanation": "The bug only shows at the boundary: 18 must be True, and `>` gives False. Test the limit and one on each side of it. The other sets pass on the buggy version." }
```

## 2. Table-driven tests: `@pytest.mark.parametrize`

In Go you'd write a `[]struct{in int; want bool}` and a `t.Run` loop. pytest builds the loop for you: you give it argument names and a list of rows, and **each row runs as its own test**.

```python
# leap.py: a seeded bug
def is_leap(year: int) -> bool:
    return year % 4 == 0
```

```python
# test_leap.py
import pytest

from leap import is_leap


@pytest.mark.parametrize("year, expected", [
    (2024, True),
    (2023, False),
    (1900, False),   # divisible by 100: not a leap year
    (2000, True),    # ...unless divisible by 400
])
def test_is_leap(year, expected):
    assert is_leap(year) == expected
```

```console
$ pytest -q
..F.                                                                     [100%]
=================================== FAILURES ===================================
___________________________ test_is_leap[1900-False] ___________________________

year = 1900, expected = False
...
>       assert is_leap(year) == expected
E       assert True == False
E        +  where True = is_leap(1900)

test_leap.py:13: AssertionError
=========================== short test summary info ============================
FAILED test_leap.py::test_is_leap[1900-False] - assert True == False
1 failed, 3 passed in 0.01s
```

What's worth noticing:

- **4 rows give 4 tests.** One failing row doesn't hide the others, unlike an assert inside a `for` loop, which stops at the first failure.
- **The test id `[1900-False]` names the failing row.** pytest builds it from the values.
- **The seeded bug survives three of the four rows.** Only the boundary rule (century years) exposes it. A table without `1900` is green on broken code.
- For awkward values, give a row a readable id: `pytest.param("   ", id="blank")`.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "A test is decorated with `@pytest.mark.parametrize(\"a, b\", [(1, 2), (3, 4), (5, 6)])`, and its body is `assert a < b`. What is the last line of `pytest -q`? (Use the format `N passed`.)",
  "code": "# shell: pytest -q (three rows, all passing)",
  "answer": "3 passed",
  "accept": ["3 passed in 0.01s", "3 passed in 0.00s"],
  "explanation": "Each row is a separate test, so a three-row table gives three tests." }
```

## 3. Testing the error path: `pytest.raises(..., match=...)`

For the "invalid" rows you assert that the right exception is raised:

```python
# percent.py
def parse_percent(text: str) -> int:
    """'42%' -> 42. Raises ValueError outside 0-100."""
    value = int(text.strip().removesuffix("%"))
    if not 0 <= value <= 100:
        raise ValueError(f"percent out of range: {value}")
    return value
```

```python
@pytest.mark.parametrize("raw", ["101%", "-1%", "abc"])
def test_rejects(raw):
    with pytest.raises(ValueError, match="out of range"):
        parse_percent(raw)
```

```console
$ pytest -q
..F                                                                      [100%]
...
>       with pytest.raises(ValueError, match="out of range"):
E       AssertionError: Regex pattern did not match.
E         Expected regex: 'out of range'
E         Actual message: "invalid literal for int() with base 10: 'abc'"
```

`'abc'` *did* raise `ValueError`, but from `int()`, not from our range check. **`match=` checks that it's the error you meant**, not just any error of that class. Here the test exposed a design question: should `'abc'` get its own clear message (wrap it with `raise ... from err`, as in L02), or is the `int()` message acceptable? Without `match`, the test would have passed and the question would never have come up.

Rules for `pytest.raises`:

- **`match` is a regular expression applied with `re.search`.** It matches anywhere in `str(exception)`, so a fragment is enough. Characters like `.`, `$`, `(` and `?` are regex syntax, so wrap a literal text in `re.escape(...)`.
- **The raising call must be the last line inside `with`.** Lines after it never run, so put extra checks after the block, using `as excinfo` and `excinfo.value`.
- **If nothing is raised, the test fails** with `Failed: DID NOT RAISE ValueError`.
- **Subclasses match too.** And never write `pytest.raises(Exception)`: it passes on a `NameError` from a typo.

```python
def test_rejects_200():
    with pytest.raises(ValueError) as excinfo:
        parse_percent("200%")
    assert str(excinfo.value) == "percent out of range: 200"
```

```quiz
{ "id": "q3", "type": "output",
  "prompt": "`match=` uses `re.search`. What does this print?",
  "code": "import re\nprint(bool(re.search(\"costs $5\", \"costs $5\")), bool(re.search(re.escape(\"costs $5\"), \"costs $5\")))",
  "answer": "False True",
  "explanation": "$ means 'end of string' in a regex, so the raw pattern can't match. re.escape turns it into a literal. Use it whenever the message you expect contains regex characters." }
```

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "In `with pytest.raises(ValueError): parse_percent(\"200%\"); assert False`, written as two lines inside the with block, the test fails because of `assert False`.", "answer": false,
  "explanation": "parse_percent raises on the first line, so the rest of the block never runs and the test passes. Checks on the exception belong after the with block." }
```

## 4. A test that would have caught the bug

When you find a bug, in your own code or in a code review, the habit is:

1. **Write a test that reproduces it,** and watch it fail. A test you have never seen fail proves nothing.
2. **Fix the code,** and watch the test pass.
3. **Keep the test.** It's now a regression test: the bug can't quietly come back.

For debugging, run `pytest -x -vv`: `-x` stops at the first failure, and `-vv` prints one line per test and never truncates the comparison:

```console
$ pytest -x -vv
test_leap.py::test_is_leap[2024-True] PASSED                             [ 25%]
test_leap.py::test_is_leap[2023-False] PASSED                            [ 50%]
test_leap.py::test_is_leap[1900-False] FAILED                            [ 75%]
...
E       assert True == False
E        +  where True = is_leap(1900)
...
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
========================= 1 failed, 2 passed in 0.01s ==========================
```

The `2000` row never ran. Fix one thing, rerun, and repeat.

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "A user reports that `slugify(\"Hello  World\")` returns `\"hello--world\"` (two dashes). What do you do first?",
  "options": [
    "Add a parametrize row (\"Hello  World\", \"hello-world\") and run it to see it fail",
    "Fix the split call, then check by hand in the REPL",
    "Add a pytest.raises test for the double space",
    "Run the existing suite with -vv to find the bug"
  ], "answer": 0,
  "explanation": "The existing suite is green, so it doesn't cover this input. A row that reproduces the report proves the bug, then proves the fix, and stays as a regression test. Checking by hand in the REPL proves it once and protects nothing." }
```

## 5. How good is a test suite? Seed a bug and see

One way to measure a suite is to **break the code on purpose** and check whether some test fails. If every test still passes on the broken code, the suite has a blind spot. Tools that do this automatically are called mutation testers. In this module's exercise, a small file does it for six hand-made bugs: your table has to catch all of them.

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "`def clamp(n, low, high)` returns n limited to the range low..high. List the rows you'd put in its parametrize table, and say what each one protects against.",
  "model": "A value inside the range (5, 0, 10 → 5): the basic case. Below low (-3 → 0) and above high (12 → 10): both directions of clamping. Exactly low (0 → 0) and exactly high (10 → 10): off-by-one comparisons (< vs <=). Negative ranges (-5, -10, -1 → -5): sign handling. low == high (7, 3, 3 → 3): a degenerate range. Possibly low > high: decide whether it raises ValueError, and test it with pytest.raises(match=).",
  "explanation": "Boundaries and degenerate inputs catch most bugs. The 'typical' row catches the fewest." }
```

## 6. Your turn: write the suite that catches the bugs

```exercise
PY.M04.L04.E1
```
