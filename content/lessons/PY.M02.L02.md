---
{
  "id": "PY.M02.L02",
  "title": "Mutable vs immutable types",
  "difficulty": "beginner",
  "minutes": 70,
  "prerequisites": ["PY.M02.L01"],
  "objectives": [
    "Classify the built-in types you use daily (int, float, str, bool, None, tuple, frozenset, list, dict, set) as mutable or immutable",
    "Predict whether an operation changes an object in place or returns a new object, including methods that return None",
    "Predict what += does on a list compared with an int, str or tuple, when another name points at the same object",
    "Explain why a tuple that holds a list can still change, and why only hashable values can be dict keys or set members"
  ],
  "why": "Whether `x += 1` or `items += [x]` changes something another part of the program can see depends entirely on the type. This is the piece of the label model that makes it predictable, and it's also why your dict keys must be tuples or strings and never lists.",
  "applications": [
    "Using tuples of fields as dict keys for grouping and caching",
    "Avoiding the `result = items.sort()` bug that leaves you holding None",
    "Spotting code that mutates a list it was only meant to read"
  ],
  "exercises": ["PY.M02.L02.E1"],
  "sources": [
    {
      "title": "Data model: Objects, values and types",
      "url": "https://docs.python.org/3.12/reference/datamodel.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Mutable objects' value can change; immutable objects' value can't", "Mutability is determined by the type: numbers, strings, tuples immutable; dicts, lists mutable", "An immutable container holding a mutable object can change value but is still considered immutable"]
    },
    {
      "title": "Programming FAQ: list y changed list x; a_tuple[i] += ['item']",
      "url": "https://docs.python.org/3.12/faq/programming.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["y.append(10) and y.sort() mutate; y = y + [10] and sorted(y) create a new object", "+= mutates lists but not tuples or ints, which create new objects", "a_tuple[0] += ['item'] extends the list and then raises TypeError on the tuple assignment"]
    },
    {
      "title": "Design and History FAQ: list.sort(); dictionary keys",
      "url": "https://docs.python.org/3.12/faq/design.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["list.sort() sorts in place and does not return the sorted list, as a reminder", "Dict keys are found by hash; a mutable key could change its hash and be lost"]
    },
    {
      "title": "Glossary: hashable, immutable, mutable",
      "url": "https://docs.python.org/3.12/glossary.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Hashable objects can be dict keys and set members", "Mutable containers (lists, dicts) are not hashable; tuples and frozensets only if their elements are hashable", "Mutable objects can change their value but keep their id()"]
    },
    {
      "title": "Augmented assignment statements",
      "url": "https://docs.python.org/3.12/reference/simple_stmts.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["x += 1 is similar to x = x + 1, but when possible the operation is performed in place, modifying the old object"]
    },
    {
      "title": "The Go Programming Language Specification: Map types",
      "url": "https://go.dev/ref/spec",
      "version": "Language version go1.27 (May 26, 2026)",
      "verified": "2026-11-12",
      "claims": ["A Go map key type must not be a function, map or slice"]
    }
  ]
}
---
## 1. Mutability belongs to the type

Last lesson, `team.append("sql")` changed a list that two names shared. Whether that can happen at all depends on the object's **type**:

| Immutable (the value can never change) | Mutable (the value can change in place) |
|---|---|
| `int`, `float`, `bool`, `str`, `None`, `tuple`, `frozenset` | `list`, `dict`, `set`, most objects of your own classes |

A mutable object keeps its identity while its value changes: `id(langs)` is the same before and after `append`. An immutable object has no operation that changes it. Try one and you get an error:

```python
word = "go"
word[0] = "G"
```

```text
TypeError: 'str' object does not support item assignment
```

Go is similar here: Go strings are immutable too. Go has no immutable slices or maps, though, so in Go you rely on convention, while in Python the type enforces it.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Which of these objects can be changed in place after it is created?",
  "options": ["`(1, 2)`", "`\"abc\"`", "`{\"a\": 1}`", "`3.14`"], "answer": 2,
  "explanation": "dict is mutable. Tuples, strings and floats are immutable: every operation on them that looks like a change builds a new object." }
```

## 2. "Changing" an immutable object builds a new one

```python
count = 10
old = count
count += 1
print(count, old, count is old)

name = "ali"
loud = name.upper()
print(name, loud)
```

```text
11 10 False
ali ALI
```

```text
count += 1        old   ───▶ 10
                  count ───▶ 11     (a new int; the label moved)

name.upper()      name ───▶ "ali"
                  loud ───▶ "ALI"   (a new string; "ali" is untouched)
```

`count += 1` didn't change the 10. It built 11 and moved the label `count`. String methods never change the string: `upper`, `strip`, `replace` and `split` all **return new objects**. A common mistake is calling `name.strip()` on its own line and expecting `name` to be stripped.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "email = \"  Ali@Example.com \"\nemail.strip()\nemail.lower()\nprint(repr(email))",
  "answer": "'  Ali@Example.com '",
  "explanation": "strip() and lower() return new strings, and here nobody keeps them. email still points at the original. You need email = email.strip().lower()." }
```

## 3. Mutating methods return None

Mutable types have both kinds of operation: some change the object, others build a new one. The FAQ's own examples are `y.sort()` (changes `y`) and `sorted(y)` (returns a new list):

```python
scores = [3, 1, 2]
ranked = sorted(scores)
print(scores, ranked)
result = scores.sort()
print(scores, result)
```

```text
[3, 1, 2] [1, 2, 3]
[1, 2, 3] None
```

Methods that change a list in place (`append`, `extend`, `sort`, `reverse`, `insert`) **return `None`** on purpose, so you can't mistake them for "give me a new list". The classic bug is `scores = scores.sort()`, which leaves `scores` bound to `None`.

```quiz
{ "id": "q3", "type": "output", "label": "Debugging",
  "prompt": "What does this print?",
  "code": "tags = [\"py\", \"go\"]\ntags = tags.append(\"sql\")\nprint(tags)",
  "answer": "None",
  "explanation": "append changes the list and returns None. The assignment then rebinds tags to that None, and the list (now with 'sql') has no label left." }
```

## 4. `+=` depends on the type

`x += y` looks like `x = x + y`, but Python performs it **in place when the type allows it**:

- On a **list**, `+=` is like `extend`: it mutates the same object.
- On an **int, str or tuple**, which can't be mutated, it builds a new object and rebinds the name.

You can only tell the difference when a second name points at the object:

```python
xs = [1, 2]
ys = xs
xs += [3]
print(xs, ys, xs is ys)

t = (1, 2)
u = t
t += (3,)
print(t, u, t is u)
```

```text
[1, 2, 3] [1, 2, 3] True
(1, 2, 3) (1, 2) False
```

```text
xs += [3]      xs ───▶ [1, 2, 3]      (same list, mutated)
               ys ────┘

t += (3,)      u ───▶ (1, 2)
               t ───▶ (1, 2, 3)       (new tuple; only t moved)
```

```quiz
{ "id": "q4", "type": "output",
  "prompt": "Careful: one line mutates, one line rebinds. What does this print?",
  "code": "a = [0]\nb = a\na += [1]\na = a + [2]\nprint(a, b)",
  "answer": "[0, 1, 2] [0, 1]",
  "explanation": "a += [1] extends the shared list, so b sees [0, 1]. a = a + [2] builds a new list and moves only a. b stays at [0, 1]." }
```

## 5. A tuple that holds a list

A tuple is immutable: **which objects it holds** is fixed forever. But if one of those objects is a list, the list itself can still change.

```python
row = ("ali", ["go"])
row[1].append("py")
print(row)
row[1] = ["rust"]
```

```text
('ali', ['go', 'py'])
TypeError: 'tuple' object does not support item assignment
```

```text
row ───▶ ( ● , ● )
           │   │
           ▼   ▼
         "ali" ["go", "py"]    ← the list can change; the tuple's arrows can't
```

The docs call this subtle: the tuple is still "immutable", but its *value* changed.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "This one surprises almost everyone (it's in the official FAQ). What does this print?",
  "code": "pair = (\"a\", [\"x\"])\ntry:\n    pair[1] += [\"y\"]\nexcept TypeError:\n    print(\"TypeError\")\nprint(pair)",
  "answer": "TypeError\n('a', ['x', 'y'])",
  "explanation": "pair[1] += [\"y\"] runs in two steps: first the list's in-place add (it extends the list, which succeeds), then pair[1] = <that list>, which fails because tuples don't support item assignment. So you get the error and the list has still changed." }
```

## 6. Only hashable values can be dict keys

A dict (or set) finds keys by their hash. If a key could change, its hash could change, and the entry would be lost. So keys must be **hashable**, which for built-ins roughly means immutable all the way down:

```python
seen = {("ali", "go"): 1}
print(seen[("ali", "go")])
bad = {["ali", "go"]: 1}
```

```text
1
TypeError: unhashable type: 'list'
```

- Strings, numbers, `None` and tuples of those are fine as keys.
- Lists, dicts and sets are not.
- A tuple containing a list is not hashable either: `hash(("ali", ["go"]))` raises the same `TypeError`.

Go has the same rule: a map key type must not be a slice, map or function. A struct of comparable fields works there, and a tuple of hashable values works here.

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "You want to count requests per (user_id, endpoint) pair in a dict. Which key works?",
  "options": ["`[user_id, endpoint]`", "`(user_id, endpoint)`", "`{user_id: endpoint}`", "`(user_id, [endpoint])`"], "answer": 1,
  "explanation": "A tuple of an int and a str is hashable. Lists and dicts aren't, and a tuple that contains a list isn't either." }
```

```quiz
{ "id": "q7", "type": "truefalse",
  "prompt": "`t = (1, [2])` is a tuple, so after any code runs, `t` will still equal `(1, [2])`.", "answer": false,
  "explanation": "The tuple will always hold the same two objects, but the list inside is mutable. After t[1].append(3), t == (1, [2, 3])." }
```

## 7. Your turn

The exercise is a **write a function** task: turn a dict of query parameters into a key you can use in a cache dict. Section 6 is the reason it's needed. Three tools you'll want: `sorted(d)` gives a dict's keys in sorted order, `isinstance(v, list)` tells you whether a value is a list, and `tuple(some_list)` builds a tuple with the same items.

```exercise
PY.M02.L02.E1
```
