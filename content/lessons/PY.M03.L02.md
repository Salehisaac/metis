---
{
  "id": "PY.M03.L02",
  "title": "Dicts and sets: counting, grouping, Counter",
  "difficulty": "beginner",
  "minutes": 50,
  "prerequisites": ["PY.M03.L01"],
  "objectives": [
    "Read a dict safely: know when d[key] raises KeyError and when to use `in` or d.get(key, default) instead",
    "Count items three ways (dict.get, defaultdict(int), Counter) and pick the clearest",
    "Group items into a dict of lists with setdefault or defaultdict(list)",
    "Use a set for de-duplication, membership tests and &, |, - between groups",
    "Predict how Counter.most_common orders equal counts, and why that isn't alphabetical"
  ],
  "why": "Counting and grouping are the core of most data handling in a backend: requests per status code, orders per customer, users per role. In Go you write a map and a loop each time. Python gives you the same map plus small tools (get, defaultdict, Counter, set) that remove the boilerplate, but each has a rule you must know, such as KeyError for a missing key, where Go would give you the zero value.",
  "applications": [
    "Counting requests per status code or events per user from a log",
    "Grouping orders by customer or rows by a foreign key before returning JSON",
    "Finding users who are in both of two groups, or in one but not the other",
    "De-duplicating IDs before a bulk query"
  ],
  "exercises": ["PY.M03.L02.E1"],
  "sources": [
    {
      "title": "Built-in Types: mapping types (dict) and set types",
      "url": "https://docs.python.org/3.12/library/stdtypes.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "dict.get(key, default) returns default if the key is missing and never raises KeyError",
        "dict.setdefault(key, default) returns the value if present, otherwise inserts default and returns it",
        "Dictionaries preserve insertion order (guaranteed since 3.7)",
        "A set is an unordered collection of distinct hashable objects, used for membership tests and removing duplicates",
        "set | other, set & other and set - other return new sets (union, intersection, difference)"
      ]
    },
    {
      "title": "collections: Container datatypes (Counter, defaultdict)",
      "url": "https://docs.python.org/3.12/library/collections.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "Counter is a dict subclass for counting hashable objects, built from an iterable",
        "A Counter returns 0 for a missing item instead of raising KeyError",
        "most_common(n) lists the n most common elements; elements with equal counts are ordered in the order first encountered",
        "defaultdict(list) groups a sequence of key-value pairs into a dictionary of lists"
      ]
    },
    {
      "title": "Python Tutorial: Data Structures (sets, dictionaries)",
      "url": "https://docs.python.org/3.12/tutorial/datastructures.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "Create a set with curly braces or set(); an empty set needs set(), because {} is an empty dict",
        "items() gives the key and value together when looping over a dict"
      ]
    }
  ]
}
---
## 1. A dict is a Go map, except for missing keys

```python
ports = {"http": 80, "https": 443}
ports["ssh"] = 22
print(ports)
print(ports["https"], len(ports), "ftp" in ports)
print(ports.get("ftp"), ports.get("ftp", 21))
ports["ftp"]
```

```console
{'http': 80, 'https': 443, 'ssh': 22}
443 3 False
None 21
KeyError: 'ftp'
```

Three differences from Go matter:

- **A missing key raises `KeyError`.** In Go, `m["ftp"]` quietly returns the zero value. Python makes you choose: `key in d` (Go's `_, ok := m[k]`), or `d.get(key, default)`, which returns the default and never raises.
- **`get` only reads.** It doesn't insert the key.
- **A dict keeps insertion order** (guaranteed since Python 3.7). Printing or looping over it gives keys in the order they were first added. Go randomises map iteration on purpose. You'll use this in L03.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "stock = {\"apple\": 3}\nprint(stock.get(\"pear\", 0))\nprint(\"pear\" in stock)\nprint(stock)",
  "answer": "0\nFalse\n{'apple': 3}", "accept": ["0\nFalse\n{'apple':3}", "0\nFalse\n{\"apple\": 3}"],
  "explanation": "get returns the default 0 for the missing key, and it doesn't insert anything, so the dict is unchanged." }
```

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "As in Go, reading `counts[\"x\"]` from a plain dict that has no key \"x\" gives 0.", "answer": false,
  "explanation": "A plain dict raises KeyError for a missing key. Use counts.get(\"x\", 0), check \"x\" in counts first, or use a Counter, which does return 0." }
```

## 2. Counting: three ways to write `counts[k]++`

Here is the same count written three ways. In the assessment you already wrote the first one correctly:

```python
from collections import Counter, defaultdict

statuses = [200, 404, 200, 500, 200, 404]

counts = {}
for code in statuses:
    counts[code] = counts.get(code, 0) + 1   # 1. plain dict + get
print(counts)

hits = defaultdict(int)                      # 2. missing key -> int() == 0
for code in statuses:
    hits[code] += 1
print(dict(hits))

c = Counter(statuses)                        # 3. Counter does the loop
print(c)
print(c[302])          # missing -> 0, no KeyError
print(c.most_common(2))
```

```console
{200: 3, 404: 2, 500: 1}
{200: 3, 404: 2, 500: 1}
Counter({200: 3, 404: 2, 500: 1})
0
[(200, 3), (404, 2)]
```

- `defaultdict(int)` calls `int()` (which returns 0) to create the value of a missing key, so `+= 1` just works. That's Go's `counts[k]++` exactly.
- `Counter` is a dict subclass made for counting. You give it any iterable, and `most_common(n)` returns the top `n` as `(item, count)` pairs.
- Which one to use: `Counter` when counting *is* the job; the `get` version when the count is one detail inside a bigger loop.

```quiz
{ "id": "q3", "type": "choice", "label": "Debugging",
  "prompt": "`counts = {}` and then `for code in [200, 404]: counts[code] += 1`. What happens?",
  "options": ["counts becomes {200: 1, 404: 1}", "KeyError: 200 on the first iteration", "counts stays {}", "TypeError: dict is not a number"], "answer": 1,
  "explanation": "counts[code] += 1 first reads counts[code], and a plain dict raises KeyError for a missing key. Use counts.get(code, 0) + 1, defaultdict(int) or Counter." }
```

## 3. The tie trap in `most_common`

The docs say **elements with equal counts are ordered in the order first encountered**. Not alphabetically, and not by any rule you choose:

```python
from collections import Counter

print(Counter(["zed", "amy", "zed", "amy", "bob"]).most_common(2))
```

```console
[('zed', 2), ('amy', 2)]
```

`zed` comes first only because it appeared first in the input. If your spec says "ties alphabetical", `most_common` alone is **wrong**, and a test whose input happens to be in alphabetical order won't catch it. L03 shows how to sort with an explicit tie-break.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "from collections import Counter\nwords = \"to be or not to be\".split()\nc = Counter(words)\nprint(c[\"be\"], c[\"maybe\"])\nprint(c.most_common(1))",
  "answer": "2 0\n[('to', 2)]", "accept": ["2 0\n[('to',2)]", "2 0\n[(\"to\", 2)]"],
  "explanation": "\"to\" and \"be\" both appear twice. most_common breaks the tie by first appearance, and \"to\" came first. A missing word like \"maybe\" counts as 0." }
```

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "`Counter(names).most_common(3)` is enough to implement \"top 3 names by count, ties in alphabetical order\".", "answer": false,
  "explanation": "most_common orders equal counts by first appearance, not alphabetically. You need an explicit sort key that includes the name (L03)." }
```

## 4. Grouping: a dict of lists

Grouping is counting's sibling: instead of adding 1, you append to a list. The two standard tools are `setdefault` and `defaultdict(list)`:

```python
from collections import defaultdict

orders = [("tehran", "A1"), ("shiraz", "B7"), ("tehran", "C3")]

by_city = defaultdict(list)
for city, order_id in orders:          # unpack each pair (more in L03)
    by_city[city].append(order_id)
print(dict(by_city))

same = {}
for city, order_id in orders:
    same.setdefault(city, []).append(order_id)
print(same)
```

```console
{'tehran': ['A1', 'C3'], 'shiraz': ['B7']}
{'tehran': ['A1', 'C3'], 'shiraz': ['B7']}
```

`setdefault(key, [])` returns the existing list, or inserts `[]` and returns it, so `.append` always has a list to work on. Both groups keep insertion order: cities in the order first seen, IDs in input order.

```quiz
{ "id": "q6", "type": "output",
  "prompt": "What does this print?",
  "code": "groups = {}\nfor w in [\"ant\", \"bee\", \"ape\"]:\n    groups.setdefault(w[0], []).append(w)\nprint(groups)",
  "answer": "{'a': ['ant', 'ape'], 'b': ['bee']}", "accept": ["{'a':['ant','ape'],'b':['bee']}", "{\"a\": [\"ant\", \"ape\"], \"b\": [\"bee\"]}"],
  "explanation": "Each word is grouped by its first letter. 'a' is inserted first (by 'ant'), so it comes first, and 'ape' is appended to the existing list." }
```

## 5. Sets: membership, de-duplication, set algebra

A set is an **unordered** collection of distinct, hashable items, like a Go `map[T]struct{}` with operators built in. `x in s` is a fast lookup. Use it to de-duplicate, test membership, and compare groups:

```python
seen = ["u3", "u1", "u3", "u2", "u1"]
unique = set(seen)
print(len(unique), "u2" in unique)
print(sorted(unique))                  # a set has no order: sort it to show it

monday = {"u1", "u2", "u3"}
tuesday = {"u2", "u4"}
print(sorted(monday & tuesday), sorted(monday | tuesday), sorted(monday - tuesday))
```

```console
3 True
['u1', 'u2', 'u3']
['u2'] ['u1', 'u2', 'u3', 'u4'] ['u1', 'u3']
```

Common mistakes:

- **`{}` is an empty dict, not an empty set.** Write `set()`.
- **Relying on set order.** The order a set of strings prints in can change from one run to the next. Sort it before you show it, compare it or return it.
- **`set(items)` loses the original order.** If order matters, keep a `seen` set next to a result list and append only the items not seen yet.

```quiz
{ "id": "q7", "type": "output",
  "prompt": "What does this print?",
  "code": "admins = {1, 2, 3}\nonline = {3, 4}\nprint(sorted(admins & online), sorted(admins | online), sorted(admins - online))\nprint(len({\"x\", \"X\".lower(), \"x\"}))",
  "answer": "[3] [1, 2, 3, 4] [1, 2]\n1", "accept": ["[3] [1,2,3,4] [1,2]\n1"],
  "explanation": "& keeps what both have, | keeps everything, - keeps what's only in the left set. The last set holds \"x\" three times, but a set keeps one copy of each item." }
```

```quiz
{ "id": "q8", "type": "truefalse",
  "prompt": "`tags = {}` creates an empty set that you can call `tags.add(\"py\")` on.", "answer": false,
  "explanation": "{} is an empty dict, which has no add method (AttributeError). An empty set is set()." }
```

## 6. Your turn: a tag index

A blog API needs tag statistics. You'll count, group and compare with the tools from this lesson. Read the requirements carefully: tags are case-insensitive, and a tag repeated inside one post counts once for that post.

```exercise
PY.M03.L02.E1
```
