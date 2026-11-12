---
{
  "id": "PY.M02.L03",
  "title": "Mutation vs rebinding across calls",
  "difficulty": "beginner",
  "minutes": 75,
  "prerequisites": ["PY.M02.L02"],
  "objectives": [
    "Explain argument passing as assignment: the parameter is a new label for the caller's object",
    "Predict whether a function call changes the caller's object, for mutation (append, item assignment, += on a list) and for rebinding (param = ...)",
    "Compare Python argument passing with Go pointers, slices and value vs pointer receivers",
    "Write functions that either mutate in place and return None, or return a new object and leave their input alone"
  ],
  "why": "In your assessment you predicted that `items = items + [99]` inside a function changes the caller's list. It doesn't, while `items.append(99)` does. Backend code passes dicts and lists between functions all day (request bodies, rows, configs), so you need to know for sure which calls can change your data.",
  "applications": [
    "Helpers that normalise a request payload without corrupting the original",
    "Reading a library's docs to see whether a function modifies its argument",
    "Debugging data that changes 'by itself' after a function call"
  ],
  "exercises": ["PY.M02.L03.E1"],
  "sources": [
    {
      "title": "Python Tutorial: Defining Functions",
      "url": "https://docs.python.org/3.12/tutorial/controlflow.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Arguments are passed by call by value, where the value is always an object reference", "Call by object reference: if a mutable object is passed, the caller sees changes the callee makes to it"]
    },
    {
      "title": "Programming FAQ: output parameters; list y changed list x",
      "url": "https://docs.python.org/3.12/faq/programming.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Arguments are passed by assignment; there is no call-by-reference alias between caller and callee names", "Return a tuple for multiple results", "+= mutates lists (like extend) but creates new objects for tuples and ints"]
    },
    {
      "title": "Assignment statements",
      "url": "https://docs.python.org/3.12/reference/simple_stmts.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Assigning to a name binds it in the current local namespace; the name is rebound if already bound", "Augmented assignment is performed in place when possible"]
    },
    {
      "title": "Design and History FAQ: Why doesn't list.sort() return the sorted list?",
      "url": "https://docs.python.org/3.12/faq/design.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["list.sort() sorts in place and does not return the sorted list, as a reminder"]
    },
    {
      "title": "The Go Programming Language Specification: Calls, Slice types, append",
      "url": "https://go.dev/ref/spec",
      "version": "Language version go1.27 (May 26, 2026)",
      "verified": "2026-11-12",
      "claims": ["Go call arguments are assigned to the function's parameters", "A slice shares storage with its underlying array and other slices of it", "append allocates a new underlying array when capacity is insufficient, otherwise reuses it"]
    }
  ]
}
---
## 1. A call is an assignment

When you call `f(team)`, Python does the equivalent of `users = team` inside the function: **the parameter becomes a new label for the same object**. Nothing is copied.

```python
def add_admin(users):
    users.append("root")

team = ["ali", "sara"]
add_admin(team)
print(team)
```

```text
['ali', 'sara', 'root']
```

```text
during the call:

  caller            add_admin
  team  ───▶ ["ali", "sara", "root"]
  users ────┘
```

Two labels, one list, exactly like `b = a` in L01. `users.append` changes the object, so the caller sees it after the call returns.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "def tag(row):\n    row[\"seen\"] = True\n\nevent = {\"id\": 1}\ntag(event)\nprint(event)",
  "answer": "{'id': 1, 'seen': True}",
  "explanation": "row is a second label for the caller's dict. Item assignment mutates that dict, so event shows the new key." }
```

## 2. Rebinding the parameter only moves the local label

This is the line from your assessment. `+` always builds a **new** list, and `=` moves the function's own label to it:

```python
def add_admin_copy(users):
    users = users + ["root"]
    return users

team = ["ali", "sara"]
result = add_admin_copy(team)
print(team)
print(result)
```

```text
['ali', 'sara']
['ali', 'sara', 'root']
```

```text
before the =       team  ───▶ ["ali", "sara"]
                   users ────┘

after the =        team  ───▶ ["ali", "sara"]
                   users ───▶ ["ali", "sara", "root"]   (new list)
```

The function's `users` is a local name. Rebinding it can't reach back and move the caller's `team`: there is no call by reference, so a function can't rebind the caller's variables. If the new list matters, the function must **return** it and the caller must keep it (`result = ...`).

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "def reset(config):\n    config = {}\n\ndef clear(config):\n    config.clear()\n\nsettings = {\"debug\": True}\nreset(settings)\nprint(settings)\nclear(settings)\nprint(settings)",
  "answer": "{'debug': True}\n{}",
  "explanation": "reset only rebinds its local label to a new empty dict; the caller's dict is untouched. clear() mutates the dict itself, which the caller sees." }
```

## 3. `+=` mutates a list, but rebinds a str or int

From L02: `+=` works in place when the type allows it. Through a parameter that matters a lot:

```python
def shout(msg):
    msg += "!"
    return msg

def extend_all(items):
    items += [0]

text = "hi"
nums = [1]
shout(text)
extend_all(nums)
print(text, nums)
```

```text
hi [1, 0]
```

- `msg += "!"`: strings can't change, so this builds `"hi!"` and rebinds the local `msg`. The caller's `text` is unchanged, and the return value was thrown away.
- `items += [0]`: lists can change, so this extends the caller's list in place.

So `items += [x]` and `items = items + [x]` behave **differently** inside a function. That's an easy mistake to make, and a good one to recognise in review.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "Two functions that look almost the same. What does this print?",
  "code": "def a(xs):\n    xs += [1]\n\ndef b(xs):\n    xs = xs + [2]\n\ndata = []\na(data)\nb(data)\na(data)\nprint(data)",
  "answer": "[1, 1]",
  "explanation": "a mutates the caller's list (+= on a list extends in place), twice. b builds a new list and rebinds only its local xs, so the 2 is lost." }
```

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "def bump(n, counts):\n    n += 1\n    counts[\"calls\"] += 1\n\nn = 0\ncounts = {\"calls\": 0}\nbump(n, counts)\nbump(n, counts)\nprint(n, counts)",
  "answer": "0 {'calls': 2}",
  "explanation": "n += 1 builds a new int and rebinds the local n; the caller's n stays 0. counts[\"calls\"] += 1 assigns into the shared dict, which is a mutation the caller sees." }
```

## 4. The Go picture

The precise Go model: **every Python name is a pointer, and Go-style "pass by value" copies the pointer.**

| Python | Go equivalent |
|---|---|
| `users.append("root")` inside the function | `func f(u *[]string) { *u = append(*u, "root") }`: changing through the pointer |
| `users = users + ["root"]` inside the function | `u = &other`: reassigning the local pointer variable, invisible to the caller |
| Every call | Like a **pointer receiver**: the method sees the caller's object. Python has no value-receiver copy. |

Two differences trip Go developers up:

- A Go **slice** shares its backing array, but `append` may allocate a new array when capacity runs out, so the caller sometimes sees the change and sometimes doesn't. A Python list has no such "sometimes": `append` and `+=` always change the one shared list, and `+` always builds a new list.
- A Go **value receiver** or a struct argument gets a copy. Python never copies on a call. If you want a copy, you make one yourself (next lesson).

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "In Go, `func set(p Point) { p.X = 9 }` doesn't change the caller's Point. What does the Python version `def set_x(p): p[\"x\"] = 9` do to a caller's dict?",
  "options": ["Nothing: Python copies arguments like Go value parameters", "Changes it: p is a second label for the caller's dict", "Raises an error: parameters are read-only", "Changes it only if the dict is small"], "answer": 1,
  "explanation": "Python passes object references by assignment. There is no copy, so mutating p mutates the caller's dict. It's closer to Go's func set(p *Point)." }
```

## 5. Pick one contract: mutate, or return new

Python's own convention, which `list.sort()` vs `sorted()` follows:

- **Mutate in place and return `None`.** The name says so (`sort`, `clear`, `add_admin`). Callers know their object changes.
- **Return a new object and leave the input alone** (`sorted`, `str.upper`, `add_admin_copy`).

The bug-prone middle is a function that mutates its argument **and** returns it. The caller writes `clean = normalise(raw)` and thinks `raw` is still the original. For data you only read, build a new list or dict and return it.

```quiz
{ "id": "q6", "type": "truefalse", "label": "Application",
  "prompt": "A helper `def strip_password(user): del user[\"password\"]; return user` is safe to call on a user dict you still need with its password later.", "answer": false,
  "explanation": "del mutates the caller's dict; returning it doesn't create a copy. The caller's original loses its password too. Build a new dict without the key instead." }
```

```quiz
{ "id": "q7", "type": "explain", "label": "Diagram",
  "prompt": "Draw the caller's and the function's labels for `def f(xs): xs.append(1); xs = [9]; xs.append(2)` called as `data = []; f(data)`. What is `data` afterwards?",
  "model": "At the call, data and xs point at one list. xs.append(1) mutates it, so it's [1]. xs = [9] moves only the local label to a new list. xs.append(2) changes that new list to [9, 2], which is thrown away when f returns. data is [1].",
  "explanation": "Mutations before the rebinding reach the caller; everything after it goes to the new local object." }
```

## 6. Your turn

The exercise is a **debugging** task with two functions in a billing helper. They have opposite bugs: one changes data it should only read, the other "changes" data in a way the caller never sees. Each function's docstring states which contract it has.

```exercise
PY.M02.L03.E1
```
