---
{
  "id": "PY.M01.L03",
  "title": "pytest: reading a test, running it, reading a failure",
  "difficulty": "beginner",
  "minutes": 35,
  "prerequisites": ["PY.M01.L02"],
  "objectives": [
    "Read a pytest test as an executable specification (arrange, act, assert)",
    "Know which files and functions pytest collects, compared with go test",
    "Run tests selectively with -q, -x, -k and a node id",
    "Use a failure report to find the failing expectation, the actual value and the line, then fix the code"
  ],
  "why": "In this academy, exercises tell you you're done by passing tests, and later you'll write your own. In your assessment you checked one example by hand, and the bug hid in the cases you didn't try. Reading test output fluently is the fastest feedback loop you'll have.",
  "applications": [
    "Running a project's test suite before and after every change",
    "Reading CI failures without rerunning everything locally",
    "Using failing tests as the to-do list while fixing a bug"
  ],
  "exercises": ["PY.M01.L03.E1"],
  "sources": [
    {
      "title": "Good Integration Practices: conventions for Python test discovery",
      "url": "https://docs.pytest.org/en/stable/explanation/goodpractices.html",
      "version": "pytest stable docs (9.x); verified locally with pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": ["pytest collects test_*.py and *_test.py files", "pytest collects test-prefixed functions, and test methods in Test-prefixed classes without __init__"]
    },
    {
      "title": "How to invoke pytest",
      "url": "https://docs.pytest.org/en/stable/how-to/usage.html",
      "version": "pytest stable docs (9.x); verified locally with pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": ["-k selects tests by keyword expression", "A test can be run by node id file::test_name", "python -m pytest also adds the current directory to sys.path"]
    },
    {
      "title": "How to handle test failures",
      "url": "https://docs.pytest.org/en/stable/how-to/failures.html",
      "version": "pytest stable docs (9.x); verified locally with pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": ["-x stops after the first failure; --maxfail=N after N"]
    },
    {
      "title": "How to write and report assertions in tests",
      "url": "https://docs.pytest.org/en/stable/how-to/assert.html",
      "version": "pytest stable docs (9.x); verified locally with pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": ["Tests use plain assert", "On failure pytest shows the values of subexpressions, including calls"]
    }
  ]
}
---
## 1. A test is an executable spec

Go tests look like `func TestCountWords(t *testing.T)` and call `t.Errorf` with a message you write yourself. pytest is simpler: a test is any function named `test_...` in a file named `test_*.py` (or `*_test.py`), and it uses Python's plain `assert`.

```python
# words.py
def count_words(text: str) -> int:
    """Number of whitespace-separated words."""
    return len(text.split(" "))
```

```python
# test_words.py
from words import count_words


def test_simple_sentence():
    assert count_words("go py go") == 3


def test_extra_spaces():
    assert count_words("go  py") == 2


def test_empty_text():
    assert count_words("") == 0
```

Read each test as one sentence of the spec: *given this input, the result must be this.* The test names say which rule they protect. Together these three tests describe more of the behaviour than the docstring does.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Which file does pytest NOT collect by default?",
  "options": ["test_words.py", "words_test.py", "check_words.py", "tests/test_api.py"], "answer": 2,
  "explanation": "Default discovery collects test_*.py and *_test.py, in subfolders too. check_words.py runs nothing: pytest reports 'no tests ran' (exit code 5)." }
```

## 2. Run it and read the failure

```console
$ pytest -q
.FF                                                                      [100%]
=================================== FAILURES ===================================
______________________________ test_extra_spaces _______________________________

    def test_extra_spaces():
>       assert count_words("go  py") == 2
E       AssertionError: assert 3 == 2
E        +  where 3 = count_words('go  py')

test_words.py:9: AssertionError
_______________________________ test_empty_text ________________________________

    def test_empty_text():
>       assert count_words("") == 0
E       AssertionError: assert 1 == 0
E        +  where 1 = count_words('')

test_words.py:13: AssertionError
=========================== short test summary info ============================
FAILED test_words.py::test_extra_spaces - AssertionError: assert 3 == 2
FAILED test_words.py::test_empty_text - AssertionError: assert 1 == 0
2 failed, 1 passed in 0.01s
```

How to read it, in this order:

1. **The progress line** `.FF`: one character per test. `.` means passed and `F` means failed.
2. **The summary at the bottom** lists which tests failed. The part after `::` is the test name, which together with the file makes its **node id**.
3. **Each failure section:**
   - `>` marks the failing line.
   - `E` lines give the comparison: `assert 3 == 2` means **got 3, expected 2**.
   - `+  where 3 = count_words('go  py')` is pytest's assertion introspection, telling you which call produced the 3.
   - `test_words.py:9` is the file and line.

You don't need print debugging to see the actual value: pytest already shows it. Now ask why `"go  py"` gives 3:

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?", "code": "print(\"go  py\".split(\" \"))",
  "answer": "['go', '', 'py']",
  "explanation": "split(\" \") cuts at every single space, so two spaces leave an empty string between them, and len() counts it. split() with no argument splits on runs of whitespace and drops the empties, which is the bug's fix." }
```

The empty-text failure has the same root cause:

```quiz
{ "id": "q6", "type": "output",
  "prompt": "What does this print?", "code": "print(\"\".split(\" \"), \"\".split())",
  "answer": "[''] []",
  "explanation": "Splitting an empty string on \" \" still gives one (empty) piece, so count_words('') returned 1. split() with no argument returns an empty list." }
```

Change `text.split(" ")` to `text.split()` and run again:

```console
$ pytest -q
...                                                                      [100%]
3 passed in 0.00s
```

## 3. Run less, faster

| Command | What it does |
|---|---|
| `pytest -q` | quiet: progress dots plus a summary |
| `pytest -x` | stop at the first failure |
| `pytest -k empty` | only tests whose name matches the expression ("1 failed, 2 deselected") |
| `pytest test_words.py::test_simple_sentence -v` | one test by node id, verbose (`PASSED` per test) |
| `pytest -x -vv` | the debugging combination: stop early, show full detail |

`python -m pytest` works too. It's the L01 rule: the pytest belonging to *that* interpreter. It also adds the current directory to the import path.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "`pytest -x` stops the run at the first failing test.", "answer": true,
  "explanation": "-x is --exitfirst. --maxfail=N stops after N failures." }
```

## 4. When a green test lies

A test that passes is only as good as what it checks. Your I1 assessment answer printed the right result for the one example and was wrong for the rest. A suite with only `test_simple_sentence` would have passed the buggy `split(" ")` version too.

That's why every exercise here ships tests for the **edge cases**: empty input, extra whitespace, ties, limits. From PY.M04 on, you'll write those tests yourself.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "A test passes on code you know is broken. What's the most likely problem?",
  "options": ["The test doesn't check the behaviour that's broken", "pytest cached an old result", "The function ran too fast to measure", "You need to run it with -vv"], "answer": 0,
  "explanation": "Tests only catch what they assert. Ask: which input would expose the bug? Then write that test, and watch it fail before you fix the code." }
```

```quiz
{ "id": "q5", "type": "explain", "label": "Debugging",
  "prompt": "A failure shows `E  AssertionError: assert [1, 2] == [1, 2, 3]` and `+  where [1, 2] = first_n([1, 2, 3, 4], 3)`. What exactly is wrong, and where would you look?",
  "model": "first_n([1, 2, 3, 4], 3) returned 2 items, but the test expected the first 3. It's one short, so look at how the slice end is computed (for example items[:n - 1] instead of items[:n]).",
  "explanation": "Got vs expected, plus the 'where' line, usually points straight at the faulty step." }
```

## 5. Your turn: fix code using only the test output

```exercise
PY.M01.L03.E1
```
