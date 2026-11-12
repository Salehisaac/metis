---
{
  "id": "PY.M03.L01",
  "title": "Lists and slicing",
  "difficulty": "beginner",
  "minutes": 50,
  "prerequisites": ["PY.M02.L04"],
  "objectives": [
    "Predict the result of a slice with out-of-range, negative or omitted bounds, using the clamping rule instead of expecting an error",
    "Use a step (including -1) to take every k-th item or reverse a list",
    "Explain why a Python slice is a new (shallow) list while a Go slice shares its backing array, and predict the effect of mutating either",
    "Replace, insert or delete a run of items with slice assignment"
  ],
  "why": "Slicing is everywhere in backend code: pagination, 'last N events', batching, dropping a header row. The clamping rule is the opposite of Go, where an out-of-range slice panics, so wrong intuitions here turn into off-by-one bugs and missing edge-case tests.",
  "applications": [
    "Paginating query results: items[offset:offset + limit]",
    "Taking the last N log lines or events: events[-n:] (with the n == 0 trap)",
    "Copying a list before changing it, so the caller's data stays untouched",
    "Splitting work into batches for a queue or a bulk insert"
  ],
  "exercises": ["PY.M03.L01.E1"],
  "sources": [
    {
      "title": "Built-in Types: common sequence operations and mutable sequence types",
      "url": "https://docs.python.org/3.12/library/stdtypes.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "Negative i or j: len(s) + i is substituted, but -0 is still 0",
        "If i or j is greater than len(s), use len(s); omitted i is 0, omitted j is len(s); i >= j gives an empty slice",
        "s.copy() creates a shallow copy, the same as s[:]",
        "s[i:j] = t replaces the slice with the contents of t; with a step k != 1, t must have the same length"
      ]
    },
    {
      "title": "Python Tutorial: An Informal Introduction to Python (lists, indexing and slicing)",
      "url": "https://docs.python.org/3.12/tutorial/introduction.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "An index that is too large is an error, but out-of-range slice indexes are handled gracefully",
        "All slice operations return a new list, so s[:] is a shallow copy",
        "Slice assignment can change the size of the list or clear it"
      ]
    }
  ]
}
---
## 1. A list is a Go slice that owns its data

A Python `list` is an ordered, growable sequence of any objects, the closest thing to a Go `[]T`. There is no separate array type and no `make`. `append` changes the list in place and returns `None`, so you never write `xs = xs.append(...)`.

```python
langs = ["go", "py", "rs"]
langs.append("js")
print(langs, len(langs))
print(langs[0], langs[-1])
langs[10]
```

```console
['go', 'py', 'rs', 'js'] 4
go js
IndexError: list index out of range
```

- `langs[-1]` is the last item. Go has no negative indices; you'd write `s[len(s)-1]`.
- **Indexing** past the end is an error, like a Go panic. Remember that, because slicing behaves differently.

## 2. Slicing: half-open, and the bounds clamp

`xs[i:j]` takes the items at positions `i <= k < j`, exactly like Go's `s[i:j]`: the start is included, the end is not. Leave out `i` and it means 0; leave out `j` and it means `len(xs)`.

The difference from Go is what happens with bounds **outside** the list. In Go, `s[3:100]` on a 5-element slice panics. In Python the docs give the rule: **if `i` or `j` is greater than `len(s)`, use `len(s)`**. A bound that is too negative is cut to 0 in the same way. Slicing never raises an IndexError; at worst you get an empty list.

```python
logs = ["boot", "auth", "db", "http", "ready"]
print(logs[1:3])
print(logs[3:100])   # end clamps to 5
print(logs[10:])     # start clamps to 5, and 5:5 is empty
print(logs[-100:2])  # start clamps to 0
```

```console
['auth', 'db']
['http', 'ready']
[]
['boot', 'auth']
```

Read a slice in two steps: **first clamp both bounds into `0..len`, then take `i <= k < j`**. If `i >= j` after clamping, the result is `[]`.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "nums = [3, 1, 2]\nprint(nums[1:3])\nprint(nums[1:99])",
  "answer": "[1, 2]\n[1, 2]", "accept": ["[1,2]\n[1,2]"],
  "explanation": "nums[1:3] is items 1 and 2 (the end is excluded). In nums[1:99] the end 99 is greater than len(nums), so it becomes 3: the same slice, no error." }
```

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "ids = [7, 8, 9]\nprint(ids[5:])\nprint(ids[-10:2])",
  "answer": "[]\n[7, 8]", "accept": ["[]\n[7,8]"],
  "explanation": "ids[5:]: the start 5 is clamped to 3, and 3:3 is empty. ids[-10:2]: -10 is before the start, so it is cut to 0, giving items 0 and 1." }
```

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "For any list `items`, `items[len(items)]` raises IndexError, but `items[len(items):]` returns `[]`.", "answer": true,
  "explanation": "Indexing a position that doesn't exist is an error. Slicing clamps its bounds, and len:len is simply empty." }
```

**Common mistake:** guarding a slice with `if len(xs) >= 3:` "so it doesn't crash". `xs[:3]` already returns at most 3 items. Guard only when you need to *know* that there were fewer.

## 3. Negative bounds and a step

A negative bound counts from the end: `len(xs) + i` is substituted. So `xs[-2:]` is "the last two" and `xs[:-1]` is "all but the last". A third number is the **step**: `xs[::2]` takes every second item, and a negative step walks backwards, so `xs[::-1]` is a reversed copy.

```python
logs = ["boot", "auth", "db", "http", "ready"]
print(logs[-2:])
print(logs[:-1])
print(logs[::2])
print(logs[::-1])
```

```console
['http', 'ready']
['boot', 'auth', 'db', 'http']
['boot', 'db', 'ready']
['ready', 'http', 'db', 'auth', 'boot']
```

With a negative step the slice runs from `i` **down** to `j`, so `i` must be the larger index: `xs[4:1:-1]` gives items 4, 3, 2, while `xs[1:4:-1]` is empty.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "xs = [0, 1, 2, 3, 4, 5]\nprint(xs[-3:])\nprint(xs[::-2])\nprint(xs[1:-1:2])",
  "answer": "[3, 4, 5]\n[5, 3, 1]\n[1, 3]", "accept": ["[3,4,5]\n[5,3,1]\n[1,3]"],
  "explanation": "-3 means len-3 = 3, so items 3 to the end. ::-2 starts at the last item and steps back two at a time: 5, 3, 1. 1:-1:2 is 1:5 stepping by 2: items 1 and 3." }
```

One trap is worth knowing by name. The docs point out that **`-0` is still `0`**. So "the last `n` items" written as `xs[-n:]` is wrong when `n` is 0:

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "xs = [10, 20, 30]\nn = 0\nprint(xs[-n:])",
  "answer": "[10, 20, 30]", "accept": ["[10,20,30]"],
  "explanation": "-n is -0, which is just 0, so the slice is xs[0:]: the whole list, not an empty one. Test n == 0 whenever you write xs[-n:]." }
```

## 4. A slice is a new list (and only a shallow copy)

In Go, `t := s[1:3]` shares `s`'s backing array, so `t[0] = 99` also changes `s`. **A Python slice builds a new list.** Changing which objects the new list holds never touches the original:

```quiz
{ "id": "q6", "type": "output",
  "prompt": "What does this print? (In Go the equivalent code would change s.)",
  "code": "s = [1, 2, 3, 4]\nt = s[1:3]\nt[0] = 99\nprint(s, t)",
  "answer": "[1, 2, 3, 4] [99, 3]", "accept": ["[1,2,3,4] [99,3]"],
  "explanation": "t is a new list holding the objects 2 and 3. t[0] = 99 rebinds a slot in t only; s is unchanged." }
```

That's why `xs[:]` (or `xs.copy()`) is the usual way to copy a list. But it's a **shallow** copy, as you saw in PY.M02: the new list holds the *same* inner objects. Mutate an inner list and both lists see it:

```python
grid = [["a"], ["b"]]
copy = grid[:]
copy.append(["c"])     # changes copy only: a new slot in the new list
copy[0].append("X")    # mutates the inner list that both share
print(grid)
print(copy)
print(copy is grid, copy[0] is grid[0])
```

```console
[['a', 'X'], ['b']]
[['a', 'X'], ['b'], ['c']]
False True
```

```quiz
{ "id": "q7", "type": "output", "label": "Debugging",
  "prompt": "A function snapshots a table before editing it. What does this print?",
  "code": "rows = [[0, 0], [1, 1]]\nsnap = rows[:]\nrows[0][0] = 5\nrows.append([2, 2])\nprint(snap)",
  "answer": "[[5, 0], [1, 1]]", "accept": ["[[5,0],[1,1]]"],
  "explanation": "snap is a new outer list, so the append doesn't show up in it. But snap[0] and rows[0] are the same inner list, so rows[0][0] = 5 is visible through snap. For a full copy of nested data use copy.deepcopy." }
```

## 5. Slice assignment: replace a run of items

On the **left** of `=`, a slice means "replace these positions with the items of this iterable". The lengths don't have to match, so the list can grow or shrink:

```python
queue = [1, 2, 3, 4, 5]
queue[1:3] = ["two", "three", "extra"]   # 2 items out, 3 in
print(queue)
queue[:2] = []                           # delete the first two
print(queue)
queue[:] = []                            # empty the same list object
print(queue)
```

```console
[1, 'two', 'three', 'extra', 4, 5]
['three', 'extra', 4, 5]
[]
```

`queue[:] = []` empties the list **in place**, so every other name bound to it sees an empty list. `queue = []` only rebinds `queue` (PY.M02). With a step (`xs[::2] = ...`) the new items must be exactly as many as the slice, or you get a ValueError.

```quiz
{ "id": "q8", "type": "output",
  "prompt": "What does this print?",
  "code": "xs = [1, 2, 3, 4, 5]\nxs[1:4] = [0]\nprint(xs)\nxs[len(xs):] = [6, 7]\nprint(xs)",
  "answer": "[1, 0, 5]\n[1, 0, 5, 6, 7]", "accept": ["[1,0,5]\n[1,0,5,6,7]"],
  "explanation": "Positions 1, 2 and 3 are replaced by one item, so the list shrinks. xs[len(xs):] is the empty slot at the end, so assigning to it appends." }
```

In everyday code, prefer the named methods when they say it better: `append`, `extend`, `insert`, `del xs[i]`, `xs.clear()`. Reach for slice assignment when you're replacing a *range*.

## 6. Your turn: pagination

Every list endpoint you've built in Go paginates. In Python the core of it is one slice, and the clamping rule handles "page past the end" for free, *if* you get the bounds right. The tests check the edges: the last partial page, a page past the end, invalid input, and the `n == 0` trap from section 3.

```console
$ .venv/bin/python tools/scaffold.py PY.M03.L01.E1
$ cd workspace/PY.M03.L01.E1 && ../../.venv/bin/pytest
```

```exercise
PY.M03.L01.E1
```
