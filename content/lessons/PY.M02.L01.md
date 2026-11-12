---
{
  "id": "PY.M02.L01",
  "title": "Names are labels: is vs ==",
  "difficulty": "beginner",
  "minutes": 70,
  "prerequisites": ["PY.M01.L03"],
  "objectives": [
    "Draw a label → object diagram for any sequence of assignments and predict what each name shows",
    "Predict when two names are aliases of one object, and when a change through one name is visible through the other",
    "Choose between == (same value) and is (same object), and explain why is must not be used to compare numbers or strings",
    "Make a separate copy of a list or dict when you need one, instead of a second name for the same object"
  ],
  "why": "In your assessment you predicted that `other = nums` copies the list. That model makes every later Python topic (function arguments, defaults, copies, shared state in a web app) unpredictable. This lesson replaces it with the real one: names are labels stuck on objects.",
  "applications": [
    "Keeping a snapshot of a record before changing it (audit logs, undo, diffs)",
    "Checking for a missing result with `is None`",
    "Reading code where two variables refer to the same request, config or cache entry"
  ],
  "exercises": ["PY.M02.L01.E1"],
  "sources": [
    {
      "title": "Data model: Objects, values and types",
      "url": "https://docs.python.org/3.12/reference/datamodel.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Every object has an identity, a type and a value", "Identity never changes once created; is compares identity; id() returns an integer for it", "CPython: id(x) is the memory address", "After a = 1; b = 1 they may or may not be the same object; after c = []; d = [] they are guaranteed different; e = f = [] is one object"]
    },
    {
      "title": "Expressions: Identity comparisons",
      "url": "https://docs.python.org/3.12/reference/expressions.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["x is y is true if and only if x and y are the same object", "Default == for objects is based on identity"]
    },
    {
      "title": "C API: Integer objects (PyLong_FromLong)",
      "url": "https://docs.python.org/3.12/c-api/long.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["The current CPython implementation keeps integer objects for -5 to 256 and returns the existing object for them"]
    },
    {
      "title": "Programming FAQ: list y changed list x; identity tests with is",
      "url": "https://docs.python.org/3.12/faq/programming.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["y = x does not copy; both names refer to one list", "a is b is equivalent to id(a) == id(b)", "Identity is guaranteed after new = old, after s[0] = x, and for singletons like None", "Don't use identity tests for int and str constants; is is the preferred way to check for None"]
    },
    {
      "title": "Python Tutorial: An Informal Introduction (Lists)",
      "url": "https://docs.python.org/3.12/tutorial/introduction.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Simple assignment never copies data; changes through one variable are seen through all others", "A full slice returns a new (shallow) copy of the list"]
    }
  ]
}
---
## 1. Assignment sticks a label on an object

In Go, `var n int = 5` gives you a box called `n` with 5 inside. Python has no boxes. **Every value is an object somewhere in memory, and a name is a label that points at one.** `x = [1, 2]` does two things: it creates a list object, then it binds the name `x` to it.

```text
x = [1, 2]

  x ───▶ [1, 2]
```

Every object has three things: an **identity** (which object it is; it never changes), a **type**, and a **value**. `id(x)` gives you the identity as a number. In CPython it's the memory address.

The closest Go picture: every Python name behaves like a pointer variable, and Python dereferences it for you. You never write `*` or `&`, but you're always handling references.

```quiz
{ "id": "q1", "type": "truefalse",
  "prompt": "After `x = [1, 2]`, the name `x` contains the list, the way a Go variable `var x [2]int` contains its array.", "answer": false,
  "explanation": "x is only a label bound to a list object. The list lives on its own; any number of names (or none) can point at it." }
```

## 2. Two labels, one object

This is the step you got wrong in the assessment. `team = langs` copies **the label**, not the list:

```python
langs = ["go", "py"]
team = langs
team.append("sql")
print(langs)
print(team is langs, id(team) == id(langs))
```

```text
['go', 'py', 'sql']
True True
```

```text
langs = ["go", "py"]     langs ───▶ ["go", "py"]

team = langs             langs ───▶ ["go", "py"]
                         team  ────┘

team.append("sql")       langs ───▶ ["go", "py", "sql"]
                         team  ────┘
```

There is only one list. `append` changed **the object**, and both labels point at it. Two names for one object are called **aliases**.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "Draw the labels first, then predict. What does this print?",
  "code": "queue = [\"a\", \"b\"]\nworking = queue\nworking.pop(0)\nprint(queue)\nprint(len(working))",
  "answer": "['b']\n1",
  "explanation": "working = queue binds a second label to the same list. pop(0) removes 'a' from that one list, so queue shows ['b'] and working has length 1." }
```

## 3. `==` asks "same value?", `is` asks "same object?"

```python
a = [1, 2, 3]
b = [1, 2, 3]
print(a == b, a is b)
c = a
print(c == a, c is a)
```

```text
True False
True True
```

```text
a ───▶ [1, 2, 3]
c ────┘
b ───▶ [1, 2, 3]        (a different list that happens to be equal)
```

- `a == b` compares **values**: same items in the same order, so `True`.
- `a is b` compares **identity**: two separate list literals always create two separate lists, so `False`. `a is b` means exactly `id(a) == id(b)`.

Go analogy: `==` is comparing `*p == *q`, while `is` is comparing `p == q`.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "x = {\"id\": 7}\ny = {\"id\": 7}\nz = y\nprint(x == y, x is y, z is y)",
  "answer": "True False True",
  "explanation": "x and y are two dicts with equal values (two {} literals are always two objects). z = y is an alias, so z is y is True." }
```

## 4. Never use `is` to compare numbers or strings

Because ints and strings are immutable (next lesson), CPython is allowed to **reuse** one object for equal values, and sometimes does. Whether two equal values are the same object depends on the value, on how it was built, and on the implementation:

```python
first = "".join(["a", "b"])
second = "ab"
print(first == second)
print(first is second)
```

```text
True
False
```

Change how the string is built and you can get `True` instead. Small ints (CPython caches -5 to 256) behave the same way: `int("200")` happens to be the cached object, `int("404")` is not. The docs say outright that this "should not be relied upon". Python 3.12 even warns when it sees `is` with a literal: `SyntaxWarning: "is" with 'int' literal. Did you mean "=="?`

**The rule:** use `==` for values. Use `is` only when identity is the question:

- `x is None`. `None` is a singleton, so there is exactly one `None` object. This is the standard way to check for "no result".
- "Is this the very same object?", for example when you're checking for aliasing, as in this lesson.

```python
def find(users, name):
    for u in users:
        if u == name:
            return u
    return None

result = find(["ali"], "bob")
print(result is None)
```

```text
True
```

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "Code that checks `status_code is 404` is fine as long as its tests pass on your machine.", "answer": false,
  "explanation": "Whether two equal ints are the same object is an implementation detail: it varies by value, by how the int was built and by interpreter. Compare values with ==; keep is for None and for real identity checks." }
```

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "`user = cache.get(key)` returns either a user dict or None. Which check is correct and idiomatic?",
  "options": ["`if user is None:`", "`if user == {}:`", "`if user is {}:`", "`if id(user) == 0:`"], "answer": 0,
  "explanation": "None is a singleton, so `is None` is guaranteed to work and is the preferred style. `user is {}` is always False: the literal creates a brand-new dict." }
```

## 5. Want a second object? Ask for one

Assignment never copies. If you want an independent list, **create a new list**: `list(old)`, `old[:]` or `old.copy()`. For a dict: `dict(old)` or `old.copy()`.

```python
langs = ["go", "py", "sql"]
backup = list(langs)
backup.append("rust")
print(langs)
print(backup)
print(backup == langs, backup is langs)
```

```text
['go', 'py', 'sql']
['go', 'py', 'sql', 'rust']
False False
```

```text
langs  ───▶ ["go", "py", "sql"]
backup ───▶ ["go", "py", "sql", "rust"]     (a new list)
```

(These copies are *shallow*: the new list holds the same item objects. L04 shows when that matters.)

The other way to "change" a name is to **rebind** it: `s = s + "thon"` builds a new object and moves the label `s` to it. Every other label stays where it was:

```quiz
{ "id": "q6", "type": "output",
  "prompt": "What does this print?",
  "code": "s = \"py\"\nt = s\ns = s + \"thon\"\nprint(s, t)",
  "answer": "python py",
  "explanation": "s + \"thon\" creates a new string and rebinds only the label s. t still points at the original \"py\". Rebinding a name never affects other names." }
```

```quiz
{ "id": "q7", "type": "output",
  "prompt": "One more, mixing both moves. What does this print?",
  "code": "a = [1]\nb = a\na = a + [2]\nb.append(3)\nprint(a, b)",
  "answer": "[1, 2] [1, 3]",
  "explanation": "b = a makes an alias. a = a + [2] builds a new list [1, 2] and moves only the label a. b still points at the original [1], so b.append(3) gives [1, 3]." }
```

```quiz
{ "id": "q8", "type": "explain", "label": "Diagram",
  "prompt": "Draw the label → object diagram after these lines, and say what `print(m)` shows: `m = {\"n\": 1}`, `k = m`, `k[\"n\"] = 2`, `k = {\"n\": 3}`.",
  "model": "After k = m both labels point at one dict. k[\"n\"] = 2 mutates that dict, so it's {\"n\": 2}. k = {\"n\": 3} creates a new dict and moves only k. Final: m ──▶ {\"n\": 2}, k ──▶ {\"n\": 3}. print(m) shows {'n': 2}.",
  "explanation": "Mutation changes the object (seen by every alias). Rebinding moves one label." }
```

## 6. Your turn

The exercise is a **debugging** task in a small audit-log module. It has two bugs, one from section 4 and one from section 5. Run pytest, read the failures, and fix the code without changing the tests.

```console
$ .venv/bin/python tools/scaffold.py PY.M02.L01.E1
$ cd workspace/PY.M02.L01.E1 && ../../.venv/bin/pytest
```

```exercise
PY.M02.L01.E1
```
