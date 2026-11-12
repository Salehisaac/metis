---
{
  "id": "PY.M03.L05",
  "title": "Comprehensions",
  "difficulty": "beginner",
  "minutes": 45,
  "prerequisites": ["PY.M03.L04"],
  "objectives": [
    "Rewrite a build-a-list loop (map and/or filter) as a list comprehension, and read one back as a loop",
    "Place a filter (`if` at the end) and a choice (`x if c else y` at the front) correctly",
    "Write dict and set comprehensions, and predict what happens with duplicate keys",
    "Read multiple for clauses in the right (outer-to-inner) order",
    "Use a generator expression with sum/any/all/max, and explain that it is lazy and can be consumed only once",
    "Decide when a plain loop is clearer than a comprehension"
  ],
  "why": "Go has no comprehensions, so every filter-and-transform is a loop with append. In Python the comprehension is the idiom: you'll read it in every codebase, FastAPI handler and test file. Reading it fluently, and knowing when not to use it, is part of writing Python that other Python developers can review.",
  "applications": [
    "Turning database rows into response objects: [to_dict(r) for r in rows]",
    "Building lookup tables: {user.id: user for user in users}",
    "Collecting distinct values: {o.customer for o in orders}",
    "Aggregates without temporary lists: sum(o.total for o in orders if o.paid)"
  ],
  "exercises": ["PY.M03.L05.E1"],
  "sources": [
    {
      "title": "Python Tutorial: Data Structures (list, set and dict comprehensions)",
      "url": "https://docs.python.org/3.12/tutorial/datastructures.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "List comprehensions build a new list by applying an operation to each item or selecting items that satisfy a condition",
        "Set and dict comprehensions are supported",
        "Prefer built-in functions to complex flow statements (nested comprehension example)",
        "It is often simpler and safer to create a new list than to change a list while looping over it"
      ]
    },
    {
      "title": "The Python Language Reference: Expressions (displays, comprehensions, generator expressions, conditional expressions)",
      "url": "https://docs.python.org/3.12/reference/expressions.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "for and if clauses nest from left to right like blocks",
        "A comprehension runs in its own scope, so names in its target list don't leak",
        "A generator expression is like a comprehension in parentheses; its values are computed lazily",
        "Parentheses can be omitted on calls with only one argument",
        "x if C else y evaluates C first"
      ]
    },
    {
      "title": "Built-in Functions: any, all, sum, max, next",
      "url": "https://docs.python.org/3.12/library/functions.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "any returns False for an empty iterable; all returns True for an empty iterable",
        "sum adds the items of an iterable starting from 0",
        "next retrieves the next item from an iterator"
      ]
    },
    {
      "title": "Glossary: iterator, generator expression",
      "url": "https://docs.python.org/3.12/glossary.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "A generator expression returns an iterator",
        "An exhausted iterator keeps raising StopIteration, so a second pass over it looks like an empty container"
      ]
    }
  ]
}
---
## 1. A list comprehension is a loop that builds a list

Here is the Go-style loop you'd write today, and the comprehension that does the same:

```python
latencies = [120, 35, 410, 80, 950]

slow = []
for ms in latencies:
    if ms > 100:
        slow.append(ms / 1000)
print(slow)

print([ms / 1000 for ms in latencies if ms > 100])
```

```console
[0.12, 0.41, 0.95]
[0.12, 0.41, 0.95]
```

Read `[EXPR for NAME in ITERABLE if COND]` in the loop's order: **for each** `ms` in `latencies`, **if** `ms > 100`, **collect** `ms / 1000`. The expression comes first because it's what goes into the list. The result is always a **new** list. As the tutorial says, building a new list is usually simpler and safer than changing the one you're looping over.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "nums = [1, 2, 3, 4, 5]\nprint([n * 10 for n in nums if n % 2])",
  "answer": "[10, 30, 50]", "accept": ["[10,30,50]"],
  "explanation": "n % 2 is 1 (truthy) for odd numbers and 0 (falsy) for even ones, so only 1, 3 and 5 pass the filter. Each is multiplied by 10." }
```

## 2. Filter vs choice: where the `if` goes

There are two different `if`s:

- **`if` at the end filters:** items that fail are left out, so the result can be shorter.
- **`x if c else y` at the front chooses a value:** every item produces something, so the result has the same length.

```python
print(["slow" if ms > 100 else "ok" for ms in latencies])
```

```console
['slow', 'ok', 'slow', 'ok', 'slow']
```

Mixing them up is a common mistake. `[ms for ms in latencies if ms > 100 else 0]` is a `SyntaxError`, because the filter `if` can't have an `else`.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "You want a label for **every** number: \"even\" or \"odd\". Which comprehension is correct?",
  "options": [
    "`[n for n in nums if n % 2 == 0 else \"odd\"]`",
    "`[\"even\" if n % 2 == 0 else \"odd\" for n in nums]`",
    "`[\"even\" for n in nums if n % 2 == 0]`",
    "`[for n in nums: \"even\" if n % 2 == 0 else \"odd\"]`"
  ], "answer": 1,
  "explanation": "A per-item choice is a conditional expression at the front. Option 1 is a SyntaxError (the filter if has no else), option 3 drops the odd numbers, and option 4 isn't Python syntax." }
```

## 3. Dict and set comprehensions

Use curly braces with `key: value` for a dict, or with a single expression for a set:

```python
users = ["Mina", "omid", "Sara"]
print({u.lower(): len(u) for u in users})

codes = {"OK": 200, "NotFound": 404}
print({code: name for name, code in codes.items()})      # invert a dict

emails = ["a@x.io", "b@y.io", "c@x.io"]
domains = {e.split("@")[1] for e in emails}               # distinct values
print(sorted(domains))
```

```console
{'mina': 4, 'omid': 4, 'sara': 4}
{200: 'OK', 404: 'NotFound'}
['x.io', 'y.io']
```

A dict comprehension assigns `result[key] = value` for each item, in order. If two items produce the **same key**, the later one silently overwrites the earlier one. That's fine for "index by id" when ids are unique, and a hidden bug when they aren't.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "print({w[0]: w for w in [\"apple\", \"avocado\", \"banana\"]})",
  "answer": "{'a': 'avocado', 'b': 'banana'}", "accept": ["{'a':'avocado','b':'banana'}", "{\"a\": \"avocado\", \"b\": \"banana\"}"],
  "explanation": "\"apple\" and \"avocado\" both produce key 'a'. The later assignment wins, but the key keeps its original position (first inserted)." }
```

## 4. Several `for` clauses, and the scope rule

More than one `for` nests **left to right, outer to inner**, in the same order you'd write the loops:

```python
print([(row, col) for row in "ab" for col in (1, 2)])
matrix = [[1, 2], [3, 4]]
print([n for row in matrix for n in row])          # flatten
```

```console
[('a', 1), ('a', 2), ('b', 1), ('b', 2)]
[1, 2, 3, 4]
```

The comprehension also has its **own scope**: its loop variable doesn't leak out, and it doesn't overwrite a variable with the same name outside.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "print([a + b for a in \"xy\" for b in \"12\"])",
  "answer": "['x1', 'x2', 'y1', 'y2']", "accept": ["['x1','x2','y1','y2']"],
  "explanation": "The first for is the outer loop. For a = 'x' the inner loop runs b = '1', '2', then the same for 'y'." }
```

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "n = 99\nsquares = [n * n for n in range(3)]\nprint(squares, n)",
  "answer": "[0, 1, 4] 99", "accept": ["[0,1,4] 99"],
  "explanation": "Inside the comprehension, n is its own variable, taking 0, 1 and 2. It doesn't leak, so the outer n is still 99. (A plain for loop would have left n == 2.)" }
```

## 5. Generator expressions: lazy, single-use

Swap the brackets for parentheses and you get a **generator expression**. It doesn't build a list; it produces values one at a time, when something asks for them. When it's the only argument of a call, you can drop the extra parentheses:

```python
latencies = [120, 35, 410, 80, 950]
print(sum(ms for ms in latencies if ms > 100))
print(any(ms > 900 for ms in latencies), all(ms > 30 for ms in latencies))

gen = (ms * 2 for ms in latencies)
print(next(gen), next(gen))
print(list(gen))
print(list(gen))
```

```console
1480
True True
240 70
[820, 160, 1900]
[]
```

- **Use one when you only consume the values once**, as with `sum`, `any`, `all`, `max`, `", ".join(...)` or `Counter(...)`. No temporary list is built, and `any` stops at the first true value.
- **It's single-use.** After it's exhausted, a second pass gets nothing: the docs say it "appears like an empty container". Store the result in a list if you need it twice.
- **Empty input:** `any(...)` is `False` and `all(...)` is `True`, which is easy to get wrong in a validation check.

```quiz
{ "id": "q6", "type": "output", "label": "Debugging",
  "prompt": "What does this print?",
  "code": "g = (x * 2 for x in [1, 2, 3])\nprint(sum(g))\nprint(sum(g))",
  "answer": "12\n0",
  "explanation": "The first sum consumes the generator: 2 + 4 + 6 = 12. The second sum gets an exhausted generator, which yields nothing, and the sum of nothing is 0. There is no error, just a wrong number." }
```

```quiz
{ "id": "q7", "type": "output",
  "prompt": "What does this print?",
  "code": "print(any(x > 0 for x in []), all(x > 0 for x in []))",
  "answer": "False True",
  "explanation": "any of nothing is False (no item is true). all of nothing is True (no item is false). So `all(field_ok(f) for f in fields)` passes when fields is empty." }
```

## 6. When not to use a comprehension

Comprehensions are for **building a value**. Prefer a plain loop when:

- **The comprehension needs more than one `for` plus an `if`, or nested conditionals.** The tutorial's own advice for a nested comprehension is to prefer a built-in (there, `zip`) over complex flow.
- **You only want side effects**, such as `[print(x) for x in xs]` or `[db.save(x) for x in xs]`. That builds a throwaway list of `None`s. Write a `for` loop.
- **You need `try`/`except`, logging or several statements per item.** A comprehension holds one expression only.

A good test: if you have to read it twice, or a reviewer asks "what does this do?", write the loop.

```quiz
{ "id": "q8", "type": "explain", "label": "Application",
  "prompt": "Would you keep this line in a code review? `ids = [u[\"id\"] for g in groups if g[\"active\"] for u in g[\"users\"] if u[\"email\"] and not u[\"email\"].endswith(\".test\")]` Explain, and say what you'd change.",
  "model": "No. It has two fors and two filters, one of them compound, so it has to be read several times. It's correct Python, but it's hard to review. Rewrite it as a loop over the active groups with an inner loop over the users, or pull the user check into a small named function (e.g. is_real_user(u)) so the comprehension becomes [u[\"id\"] for g in active_groups for u in g[\"users\"] if is_real_user(u)].",
  "explanation": "Comprehensions are about readability. Once the logic needs explaining, a loop or a named helper is clearer." }
```

## 7. Your turn: an orders report

Five small functions over a list of order dicts. Each can be a single `return` with a list, dict or set comprehension, or a generator expression. Choose the right one for each, and watch the edges: empty input, duplicates and strict vs non-strict comparisons.

```exercise
PY.M03.L05.E1
```
