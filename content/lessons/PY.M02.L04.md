---
{
  "id": "PY.M02.L04",
  "title": "Copies and the mutable-default-argument trap",
  "difficulty": "beginner",
  "minutes": 75,
  "prerequisites": ["PY.M02.L03"],
  "objectives": [
    "Make shallow copies four ways (slice, list()/dict(), .copy(), copy.copy) and predict what they share with the original",
    "Predict slice results when the bounds run past the end of a list (they clamp, no error)",
    "Choose copy.deepcopy when nested mutable objects must not be shared, and know its costs",
    "Explain why a mutable default argument is shared between calls and fix it with the None sentinel"
  ],
  "why": "Shallow copies, [[0] * n] * m grids and `def f(x, items=[])` are three of the most common sources of 'my data changed by itself' bugs in real Python code, including web apps where a module-level default lives as long as the server process. You also missed slice clamping twice in your assessment; slices are a copy tool, so it comes back here.",
  "applications": [
    "Copying a default config before customising it per environment or per request",
    "Building grids and tables without shared rows",
    "Writing functions with optional list/dict parameters that don't leak state between calls"
  ],
  "exercises": ["PY.M02.L04.E1"],
  "sources": [
    {
      "title": "copy: Shallow and deep copy operations",
      "url": "https://docs.python.org/3.12/library/copy.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Assignment doesn't copy; it creates bindings", "A shallow copy inserts references to the original's objects; a deep copy inserts copies, recursively", "Deep copy can copy too much and must handle recursive objects; deepcopy keeps a memo dict", "Shallow copies of dicts via dict.copy(), of lists via a full slice"]
    },
    {
      "title": "Built-in Types: Common and mutable sequence operations",
      "url": "https://docs.python.org/3.12/library/stdtypes.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["In a slice s[i:j], an i or j greater than len(s) is replaced by len(s)", "Items in s * n are not copied but referenced multiple times ([[]] * 3)", "s.copy() creates a shallow copy, same as s[:]"]
    },
    {
      "title": "Python Tutorial: An Informal Introduction (Lists, Text)",
      "url": "https://docs.python.org/3.12/tutorial/introduction.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["All slice operations return a new list; a full slice is a shallow copy", "Out of range slice indexes are handled gracefully, while indexing out of range raises IndexError"]
    },
    {
      "title": "Compound statements: Function definitions (default parameter values)",
      "url": "https://docs.python.org/3.12/reference/compound_stmts.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Default values are evaluated once, when the def is executed, and the same value is used for each call", "A mutated mutable default stays modified; use None as the default and test for it"]
    },
    {
      "title": "Python Tutorial: Default Argument Values",
      "url": "https://docs.python.org/3.12/tutorial/controlflow.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["The default is evaluated only once; f(a, L=[]) accumulates across calls", "Fix: L=None, then create a new list inside the function"]
    },
    {
      "title": "Programming FAQ: default values shared; copying; multidimensional lists",
      "url": "https://docs.python.org/3.12/faq/programming.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Default values are created exactly once; immutable defaults (numbers, strings, tuples, None) are safe", "Use copy.copy() or copy.deepcopy(); sequences can be copied by slicing", "Replicating a list with * creates references to the same inner list"]
    },
    {
      "title": "The Go Programming Language Specification: Slice expressions",
      "url": "https://go.dev/ref/spec",
      "version": "Language version go1.27 (May 26, 2026)",
      "verified": "2026-11-12",
      "claims": ["Slicing a slice shares the underlying array with the operand", "Slice indices beyond cap(a) are out of range and cause a run-time panic"]
    }
  ]
}
---
## 1. Shallow copies, and slices that clamp

You already met `list(x)` and `x[:]` in L01. The full set of **shallow copy** tools:

| For a list | For a dict | For anything |
|---|---|---|
| `old[:]`, `list(old)`, `old.copy()` | `dict(old)`, `old.copy()` | `copy.copy(old)` |

Every slice builds a new list, not only `[:]`. And slice bounds that run past the end **clamp** to the length instead of raising. Only indexing raises `IndexError`.

```python
ports = [80, 443, 8080]
print(ports[1:99], ports[5:], ports[:])
first_two = ports[:2]
first_two.append(22)
print(ports, first_two)
```

```text
[443, 8080] [] [80, 443, 8080]
[80, 443, 8080] [80, 443, 22]
```

Go is stricter here: `s[1:99]` on a slice with capacity 3 panics, and a Go sub-slice **shares** its backing array with the original. A Python slice of a list is always a new list.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "Slices again (you missed clamping twice, so slow down). What does this print?",
  "code": "ids = [10, 20, 30, 40]\ntail = ids[2:10]\ntail[0] = 99\nprint(tail, ids[3:100], ids[4:])\nprint(ids)",
  "answer": "[99, 40] [40] []\n[10, 20, 30, 40]",
  "explanation": "ids[2:10] clamps the end to 4 and builds a new list [30, 40]; changing it doesn't touch ids. ids[3:100] clamps to [40]. ids[4:] starts at the length, so it's empty. No IndexError anywhere: only ids[10] would raise." }
```

## 2. Shallow means "new outer, same inner"

A shallow copy is a **new container** whose slots point at **the same item objects**. With immutable items (ints, strings) that's all you need. With nested lists or dicts, the inner objects are shared:

```python
servers = [["web1", "web2"], ["db1"]]
shallow = list(servers)
shallow.append(["cache1"])
shallow[0].append("web3")
print(servers)
print(shallow)
print(shallow is servers, shallow[0] is servers[0])
```

```text
[['web1', 'web2', 'web3'], ['db1']]
[['web1', 'web2', 'web3'], ['db1'], ['cache1']]
False True
```

```text
servers ───▶ [ A, B ]
shallow ───▶ [ A, B, C ]       (a different outer list)

A ───▶ ["web1", "web2", "web3"]   shared by both
B ───▶ ["db1"]                    shared by both
C ───▶ ["cache1"]                 only in shallow
```

`shallow.append(...)` changed only the new outer list. `shallow[0].append(...)` went through a shared inner list, so `servers` sees it.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "user = {\"name\": \"ali\", \"roles\": [\"dev\"]}\nclone = user.copy()\nclone[\"name\"] = \"sara\"\nclone[\"roles\"].append(\"admin\")\nprint(user)",
  "answer": "{'name': 'ali', 'roles': ['dev', 'admin']}",
  "explanation": "user.copy() is shallow. clone[\"name\"] = ... rebinds a slot in the new dict only. clone[\"roles\"] is the same list object as user[\"roles\"], so append is visible through user." }
```

## 3. `copy.deepcopy`: copy all the way down

`copy.deepcopy(x)` builds a new outer object and, recursively, **copies** every object inside it:

```python
import copy

DEFAULT_CONFIG = {"debug": False, "hosts": ["localhost"]}
dev = copy.copy(DEFAULT_CONFIG)
dev["debug"] = True
dev["hosts"].append("dev.local")
print(DEFAULT_CONFIG)
prod = copy.deepcopy(DEFAULT_CONFIG)
prod["hosts"].append("prod.example.com")
print(DEFAULT_CONFIG)
print(prod)
```

```text
{'debug': False, 'hosts': ['localhost', 'dev.local']}
{'debug': False, 'hosts': ['localhost', 'dev.local']}
{'debug': False, 'hosts': ['localhost', 'dev.local', 'prod.example.com']}
```

The shallow `dev` copy corrupted the shared default config. The deep `prod` copy didn't. (`prod` contains `dev.local` only because it was copied *after* `dev` had already changed the default; its own `append` stayed out of `DEFAULT_CONFIG`.)

**Limits:** `deepcopy` is slower and copies *everything*, including data you may have wanted to share (say, a big lookup table that every copy should reuse). It keeps a memo of objects already copied, so a structure that contains itself doesn't loop forever. Use shallow copies when items are immutable, and `deepcopy` when nested mutable data must be independent.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import copy\nmatrix = [[1, 2], [3, 4]]\na = copy.copy(matrix)\nb = copy.deepcopy(matrix)\nmatrix[0][0] = 9\nprint(a[0][0], b[0][0])",
  "answer": "9 1",
  "explanation": "a is a new outer list holding the same row lists, so it sees matrix[0][0] = 9. b copied the rows too, so it keeps 1." }
```

## 4. The `[[0] * n] * m` grid trap

`*` on a list repeats **references**, not copies. For a list of numbers that's harmless; for a list of lists, every row is the same row:

```python
grid = [[0] * 3] * 2
grid[0][0] = 1
print(grid)
grid = [[0] * 3 for _ in range(2)]
grid[0][0] = 1
print(grid)
```

```text
[[1, 0, 0], [1, 0, 0]]
[[1, 0, 0], [0, 0, 0]]
```

The second form (a list comprehension, covered in PY.M03) evaluates `[0] * 3` once **per row**, so each row is a new list.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "board = [[\".\"] * 2] * 3\nboard[1][1] = \"X\"\nprint(len(board), board[0])",
  "answer": "3 ['.', 'X']",
  "explanation": "All three slots of board point at one inner list, so setting board[1][1] changes the row you see through board[0] as well." }
```

## 5. Default values are created once

A `def` statement runs once, and **that is when default values are evaluated**. The default object is stored on the function and reused by every call that doesn't pass the argument:

```python
def log_line(msg, lines=[]):
    lines.append(msg)
    return lines

print(log_line("start"))
print(log_line("stop"))
print(log_line.__defaults__)
```

```text
['start']
['start', 'stop']
(['start', 'stop'],)
```

```text
log_line.__defaults__ ───▶ ( ● ,)
                             │
call 1: lines ───────────────┤
call 2: lines ───────────────┴──▶ ["start", "stop"]   (one list, forever)
```

It's L03 again: `lines` is a label for an object, and here that object outlives every call. In a web server the function lives as long as the process, so this list keeps growing across requests and leaks one user's data into another's response.

Immutable defaults (`0`, `""`, `None`, `()`) are safe, because nothing can change them. Go has no default arguments; the closest Go equivalent is a package-level `var` slice that every call appends to.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "def visit(page, history={}):\n    history[page] = history.get(page, 0) + 1\n    return history\n\nvisit(\"home\")\nvisit(\"about\", {})\nprint(visit(\"home\"))",
  "answer": "{'home': 2}",
  "explanation": "The default dict is created once. Call 1 puts home: 1 into it. Call 2 passes its own new dict, so the default isn't touched. Call 3 uses the default again: home becomes 2." }
```

## 6. The fix: `None` as the default

Use `None` (immutable, a singleton) as the default, and create a new object **inside** the function, on every call:

```python
def remember(word, seen=None):
    if seen is None:
        seen = []
    seen.append(word)
    return seen

print(remember("a"))
print(remember("b"))
mine = ["x"]
print(remember("c", mine), mine)
```

```text
['a']
['b']
['x', 'c'] ['x', 'c']
```

- The new `[]` runs on every call, so calls don't share it.
- Test with `is None`, not `if not seen:` and not `seen = seen or []`. Those also replace an **empty list the caller passed in**, so the caller's list never gets the item:

```python
def remember_or(word, seen=None):
    seen = seen or []
    seen.append(word)
    return seen

mine = []
remember_or("c", mine)
print(mine)
```

```text
[]
```

```quiz
{ "id": "q6", "type": "output",
  "prompt": "This version uses the sentinel. What does this print?",
  "code": "def enqueue(job, queue=None):\n    if queue is None:\n        queue = []\n    queue.append(job)\n    return queue\n\nenqueue(\"a\")\nq = enqueue(\"b\")\nshared = []\nenqueue(\"c\", shared)\nenqueue(\"d\", shared)\nprint(q, shared)",
  "answer": "['b'] ['c', 'd']",
  "explanation": "Without an argument, each call creates its own new list, so q holds only 'b'. When the caller passes a list, the function mutates that list (L03), so shared collects 'c' and 'd'." }
```

```quiz
{ "id": "q7", "type": "choice", "label": "Debugging",
  "prompt": "Users of a FastAPI service occasionally see another user's items in their cart. The handler calls `def build_cart(user_id, items=[]): items.append(...); return {\"user\": user_id, \"items\": items}`. What's the root cause?",
  "options": ["The default list is created once and shared by every call in the server process", "FastAPI runs handlers in threads, so lists get mixed up", "append is not thread-safe", "The dict literal is cached between calls"], "answer": 0,
  "explanation": "The default list is evaluated once, when def runs, and lives as long as the process. Every call without items appends to that same list. Use items=None and create a new list inside." }
```

## 7. Your turn

The exercise is a **debugging** task: an order factory whose orders share state with each other, with a module-level template, and with the caller. Section 3 and section 6 are the tools. Each test creates its own orders and checks they're independent.

```exercise
PY.M02.L04.E1
```
