---
{
  "id": "PY.M03.L03",
  "title": "Tuples, unpacking, sorting with key= and tie-breaks",
  "difficulty": "intermediate",
  "minutes": 55,
  "prerequisites": ["PY.M03.L02"],
  "objectives": [
    "Build tuples (including the one-item tuple) and use them as fixed records and dict keys",
    "Unpack tuples in assignments and for loops, including dict.items() and enumerate",
    "Choose between sorted() (new list) and list.sort() (in place, returns None)",
    "Write a key= function with a tuple key for multi-key sorts: descending numbers via negation, ascending tie-break by name",
    "Explain why reverse=True can't express 'count descending, name ascending', and why insertion order is not a ranking"
  ],
  "why": "\"Top N, ties alphabetical\" is one of the most common requirements in backend code (leaderboards, top endpoints, most active users), and it is exactly the task that failed in your assessment: no sort, no tie-break, and an order that changed between runs. In Python the whole ranking is one sorted() call with the right key, but only if you understand tuple comparison, key functions and stability.",
  "applications": [
    "Leaderboards and 'top N' reports with deterministic tie-breaks",
    "Sorting API results by several fields (status, then date, then id)",
    "Composite dict keys such as (user_id, day) for per-user, per-day counters",
    "Returning multiple values from a function and unpacking them at the call site"
  ],
  "exercises": ["PY.M03.L03.E1"],
  "sources": [
    {
      "title": "Python Tutorial: Data Structures (tuples, sequence unpacking, comparing sequences)",
      "url": "https://docs.python.org/3.12/tutorial/datastructures.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "Tuples are immutable; a one-item tuple needs a trailing comma",
        "Tuple packing and sequence unpacking; unpacking needs as many names as items; multiple assignment combines the two",
        "Tuples of strings, numbers or tuples can be dict keys; lists can't",
        "Sequences compare lexicographically: the first differing items decide"
      ]
    },
    {
      "title": "Sorting Techniques (HOWTO)",
      "url": "https://docs.python.org/3.12/howto/sorting.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "sorted() returns a new list; list.sort() sorts in place and returns None",
        "The key function is called exactly once for each input record",
        "Both accept reverse=True for descending sorts",
        "Sorts are guaranteed to be stable, and reverse keeps stability; this allows multi-pass sorts (secondary key first)"
      ]
    },
    {
      "title": "Built-in Functions: sorted, enumerate",
      "url": "https://docs.python.org/3.12/library/functions.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "sorted(iterable, *, key=None, reverse=False) returns a new sorted list; key and reverse are keyword-only",
        "sorted() is guaranteed to be stable",
        "enumerate(iterable, start=0) yields (count, value) tuples"
      ]
    },
    {
      "title": "The Python Language Reference: Expressions (value comparisons)",
      "url": "https://docs.python.org/3.12/reference/expressions.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Strings compare lexicographically by Unicode code point (ord), so 'Z' < 'a'", "Tuples and lists are ordered by their first unequal elements; a shorter prefix sorts first"]
    },
    {
      "title": "Built-in Types: dict insertion order",
      "url": "https://docs.python.org/3.12/library/stdtypes.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Dictionaries preserve insertion order; updating a key does not change the order (guaranteed since 3.7)"]
    }
  ]
}
---
## 1. Tuples: small fixed records

A tuple is an **immutable** sequence. Lists usually hold many items of one kind; tuples usually hold a few fields that belong together, like a small anonymous Go struct. The comma makes the tuple; the parentheses are only for grouping:

```python
point = 3, 4
print(point, type(point).__name__)
visits = {("tehran", "mon"): 120, ("tehran", "tue"): 95}
print(visits[("tehran", "mon")])
{["tehran", "mon"]: 1}
```

```console
(3, 4) tuple
120
TypeError: unhashable type: 'list'
```

- **Tuples can be dict keys** (if what they contain is immutable too), so `(city, day)` works as a composite key. Lists can't be keys, because they can change. In Go you'd declare a `struct{city, day string}` key type.
- **A one-item tuple needs a trailing comma:** `("admin",)`. Without the comma, `("admin")` is just the string in parentheses.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "a = (\"admin\")\nb = (\"admin\",)\nprint(len(a), len(b))",
  "answer": "5 1",
  "explanation": "(\"admin\") is just the string \"admin\" (5 characters). The trailing comma in (\"admin\",) makes a one-item tuple." }
```

## 2. Unpacking: names on the left, a sequence on the right

**Sequence unpacking** assigns each item to its own name. Go does this only for multiple return values; Python does it for any sequence, and in `for` loops too:

```python
a, b = 1, 2
a, b = b, a                     # swap: pack the right side, then unpack it
print(a, b)

scores = {"mina": 72, "omid": 91}
for name, score in scores.items():      # items() yields (key, value) tuples
    print(name, score)

for rank, name in enumerate(["omid", "mina"], start=1):
    print(rank, name)

first, second = ("a", "b", "c")
```

```console
2 1
mina 72
omid 91
1 omid
2 mina
ValueError: too many values to unpack (expected 2)
```

`enumerate` is Go's `for i, v := range s`, and `start=1` gives you human-friendly ranks. The number of names must match the number of items, or you get a ValueError.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "for i, name in enumerate([\"ana\", \"bo\"], start=1):\n    print(i, name)\npairs = [(\"a\", 1), (\"b\", 2)]\nfor letter, n in pairs:\n    print(letter * n)",
  "answer": "1 ana\n2 bo\na\nbb",
  "explanation": "enumerate yields (count, item) pairs starting at 1. Each pair in pairs is unpacked into letter and n, and a string times n repeats it." }
```

## 3. `sorted()` vs `.sort()`

- `sorted(anything)` returns a **new list** and leaves its input alone. It accepts any iterable: a list, a dict (its keys), `d.items()`, a set.
- `xs.sort()` sorts a list **in place** and returns `None`, the same convention as `append`.

```python
nums = [3, 1, 2]
print(sorted(nums), nums)
result = nums.sort()
print(result, nums)
```

```console
[1, 2, 3] [3, 1, 2]
None [1, 2, 3]
```

**Common mistakes:**

- `xs = xs.sort()` sets `xs` to `None`.
- Calling `.sort()` on a list the caller passed in. You've just changed their data (PY.M02). Use `sorted()` when the input isn't yours.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "names = [\"b\", \"a\"]\nordered = sorted(names)\nnames.sort(reverse=True)\nprint(ordered, names)",
  "answer": "['a', 'b'] ['b', 'a']", "accept": ["['a','b'] ['b','a']", "[\"a\", \"b\"] [\"b\", \"a\"]"],
  "explanation": "sorted made a new ascending list. names.sort(reverse=True) then sorted the original list in place, descending. The two lists are separate objects." }
```

## 4. `key=`: sort by something computed

By default items are compared directly. `key=` takes a function of one item and sorts by its result instead. The docs note that it's called **exactly once per item**, so it's cheap. Strings compare by code point, so every uppercase letter sorts before every lowercase one. A key fixes that:

```python
print(sorted(["Banana", "apple", "cherry"]))
print(sorted(["Banana", "apple", "cherry"], key=str.lower))
print(sorted(["kiwi", "fig", "banana"], key=len))
```

```console
['Banana', 'apple', 'cherry']
['apple', 'Banana', 'cherry']
['fig', 'kiwi', 'banana']
```

`lambda x: ...` is an inline one-expression function, like a Go `func(x T) K { return ... }` literal. You'll use it constantly for keys.

**Tuples compare item by item:** the first items that differ decide, and later items only matter when everything before them is equal. So `(2, "b") < (2, "c")` because the first items tie, and `(1, "z") < (2, "a")` because `1 < 2` settles it. That's what makes multi-key sorting work.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "print(sorted([\"Zoe\", \"adam\", \"Bob\"]))\nprint(sorted([\"Zoe\", \"adam\", \"Bob\"], key=str.lower))",
  "answer": "['Bob', 'Zoe', 'adam']\n['adam', 'Bob', 'Zoe']", "accept": ["['Bob','Zoe','adam']\n['adam','Bob','Zoe']"],
  "explanation": "Without a key, uppercase letters sort before lowercase ones, so 'adam' goes last. key=str.lower compares lowercased copies (the items themselves are unchanged)." }
```

## 5. Multi-key sorts and the tie-break

The requirement is a leaderboard: **highest score first; equal scores in alphabetical order by name.** Return a key tuple that sorts ascending in exactly that priority:

```python
scores = {"mina": 72, "sara": 91, "omid": 91, "ali": 72, "reza": 60}
board = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
print(board)
print(board[:3])
```

```console
[('omid', 91), ('sara', 91), ('ali', 72), ('mina', 72), ('reza', 60)]
[('omid', 91), ('sara', 91), ('ali', 72)]
```

- `-item[1]` turns "score descending" into "negative score ascending", so 91 (as -91) comes before 72 (as -72).
- `item[0]` only matters when the scores tie, and then it sorts names A to Z.
- `board[:3]` is "top 3". Thanks to slice clamping (L01), it also works when there are fewer than 3 players.

Now the tempting wrong version:

```python
wrong = sorted(scores.items(), key=lambda item: (item[1], item[0]), reverse=True)
print(wrong)
```

```console
[('sara', 91), ('omid', 91), ('mina', 72), ('ali', 72), ('reza', 60)]
```

`reverse=True` reverses the **whole** comparison, so the names come out Z to A inside each tie. A test with no ties, or with tied names already in this order, passes anyway. That's why the tie must be in your tests.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "Products: most expensive first, equal prices by name A to Z. What does this print?",
  "code": "items = [(\"pen\", 2), (\"cup\", 5), (\"ink\", 2), (\"bag\", 5)]\nprint(sorted(items, key=lambda p: (-p[1], p[0])))",
  "answer": "[('bag', 5), ('cup', 5), ('ink', 2), ('pen', 2)]", "accept": ["[('bag',5),('cup',5),('ink',2),('pen',2)]"],
  "explanation": "The key for ('cup', 5) is (-5, 'cup'). The -5 items come first, and within them names sort ascending: bag, cup. Then the -2 items: ink, pen." }
```

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "`counts` is a dict of name -> count. Which call ranks by count descending, ties alphabetical?",
  "options": [
    "`sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)`",
    "`sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))`",
    "`sorted(counts.items(), key=lambda kv: kv[1], reverse=True)`",
    "`sorted(counts.items(), key=lambda kv: (-kv[1], -kv[0]))`"
  ], "answer": 1,
  "explanation": "Only option 2 is descending on count and ascending on name. Option 1 makes ties Z to A. Option 3 leaves ties in input order. Option 4 raises TypeError, because you can't negate a string." }
```

**What about descending strings?** You can't negate a string. Use **stability** instead (next section): sort by the secondary key first, then by the primary key.

## 6. Stability, and why insertion order is not a ranking

Python's sort is **stable**: items whose keys are equal keep their relative order from the input, and `reverse=True` keeps that guarantee. This lets you sort in passes, secondary key first:

```python
tickets = [("bug", "omid"), ("feature", "ali"), ("bug", "ali"), ("feature", "sara")]
print(sorted(tickets, key=lambda t: t[0]))                  # ties keep input order
by_owner_desc = sorted(tickets, key=lambda t: t[1], reverse=True)
print(sorted(by_owner_desc, key=lambda t: t[0]))            # type A-Z, owner Z-A
```

```console
[('bug', 'omid'), ('bug', 'ali'), ('feature', 'ali'), ('feature', 'sara')]
[('bug', 'omid'), ('bug', 'ali'), ('feature', 'sara'), ('feature', 'ali')]
```

```quiz
{ "id": "q7", "type": "output",
  "prompt": "What does this print?",
  "code": "jobs = [(\"b\", 2), (\"a\", 1), (\"c\", 2)]\nprint(sorted(jobs, key=lambda j: j[1], reverse=True))",
  "answer": "[('b', 2), ('c', 2), ('a', 1)]", "accept": ["[('b',2),('c',2),('a',1)]"],
  "explanation": "Sorted by the number, descending. 'b' and 'c' tie at 2, and reverse=True keeps stability, so they stay in input order: b before c." }
```

**Go comparison.** In Go, ranging over a map gives a different order on different runs, so "top N" without a sort is visibly broken. A Python dict is the opposite trap: it **preserves insertion order**, so output looks stable and plausible. But insertion order is just "first seen", not "most first". You still need `sorted(..., key=...)` with an explicit tie-break. Go's equivalent is `sort.Slice` with a less function that compares counts and then names.

```quiz
{ "id": "q8", "type": "truefalse",
  "prompt": "Because a dict preserves insertion order, looping over a dict of message counts lists senders from most to fewest messages.", "answer": false,
  "explanation": "Insertion order is the order keys were first added, which has nothing to do with the counts. You must sort by count, and add a tie-break." }
```

## 7. Your turn: top senders, in Python

This is the ranking problem from your assessment, now with tests. Before you write code, read the contract and say out loud what `n` means. Then look at the test names: they tell you which edges matter (ties at the cutoff, `n` larger than the number of senders, `n == 0`, empty input, and not changing the caller's list).

```exercise
PY.M03.L03.E1
```
