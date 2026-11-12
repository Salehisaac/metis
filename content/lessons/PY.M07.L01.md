---
{
  "id": "PY.M07.L01",
  "title": "Iteration protocol and generators",
  "difficulty": "intermediate",
  "minutes": 45,
  "prerequisites": ["PY.M04.L02", "PY.M05.L01"],
  "objectives": [
    "Explain what a for loop does in terms of iter(), next() and StopIteration",
    "Tell an iterable (fresh pass every time) from an iterator (single pass) and predict what a second pass over an exhausted iterator returns",
    "Write a generator function with yield and predict when its body runs",
    "Chain generators into a lazy pipeline that handles one item at a time and works on endless input"
  ],
  "why": "Files, database cursors, HTTP streaming responses and queue consumers are all iterators in Python. Knowing that they are lazy and single-pass is what keeps you from loading a 2 GB file into memory, or from looping over an already-consumed result and getting nothing back with no error.",
  "applications": [
    "Processing large files line by line in constant memory",
    "Streaming rows from a database cursor instead of fetching them all",
    "Building data-processing pipelines (parse, filter, limit) from small testable steps"
  ],
  "exercises": ["PY.M07.L01.E1"],
  "sources": [
    {
      "title": "Python Tutorial: Classes, 9.8 Iterators, 9.9 Generators, 9.10 Generator Expressions",
      "url": "https://docs.python.org/3.12/tutorial/classes.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["for calls iter() on the container; the iterator's __next__() returns items and raises StopIteration at the end", "next() calls __next__()", "A generator resumes where it left off and saves its local state between calls", "Generators raise StopIteration automatically when they finish", "Generator expressions use parentheses and are more memory friendly than list comprehensions"]
    },
    {
      "title": "Built-in Types: Iterator Types and Generator Types",
      "url": "https://docs.python.org/3.12/library/stdtypes.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["The iterator protocol is __iter__() returning the iterator itself plus __next__()", "Once __next__() raises StopIteration it must keep doing so", "A generator object supplies __iter__() and __next__()"]
    },
    {
      "title": "Glossary: iterable, iterator, generator, generator iterator",
      "url": "https://docs.python.org/3.12/glossary.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["A container produces a fresh iterator each time it is passed to iter()", "An exhausted iterator used in a second pass looks like an empty container", "Each yield suspends the generator, remembering local variables and pending try statements"]
    },
    {
      "title": "Package iter (Go standard library)",
      "url": "https://pkg.go.dev/iter",
      "version": "pkg.go.dev page for go1.27.4 (Go code in this lesson run with go1.21.0)",
      "verified": "2026-11-12",
      "claims": ["type Seq[V any] func(yield func(V) bool)", "An iterator is a function that passes successive elements to a callback conventionally named yield", "The iterator stops when the sequence ends or yield returns false", "Some iterators are single-use"]
    },
    {
      "title": "Go 1.23 Release Notes",
      "url": "https://go.dev/doc/go1.23",
      "version": "Go 1.23",
      "verified": "2026-11-12",
      "claims": ["for-range accepts iterator functions func(func() bool), func(func(K) bool), func(func(K, V) bool)", "The new iter package provides definitions for user-defined iterators"]
    }
  ]
}
---
## 1. What `for` actually does

In Go, `for range` is built into the language for a fixed list of things: slices, maps, strings, channels (and, since Go 1.23, iterator functions). In Python, **every** `for` loop goes through one small protocol, and anything that follows the protocol can be looped over:

1. `for` calls `iter(obj)` to get an **iterator**.
2. It calls `next(iterator)` again and again; each call returns the next item.
3. When there are no more items, `next` raises `StopIteration`, and the loop ends quietly.

You can do it by hand:

```python
langs = ["go", "py"]
it = iter(langs)
print(it)
print(next(it))
print(next(it))
try:
    next(it)
except StopIteration:
    print("StopIteration: the loop ends here")
```

```console
<list_iterator object at 0x7b663198de10>
go
py
StopIteration: the loop ends here
```

So `for lang in langs: print(lang)` is roughly this `while` loop:

```python
it = iter(langs)
while True:
    try:
        lang = next(it)
    except StopIteration:
        break
    print(lang)
```

Yes, Python ends **every** loop with an exception. In Go an exception-like panic for normal control flow would be wrong; in Python, `StopIteration` is just the agreed "no more items" signal, and `for` catches it for you. `next(it, default)` returns `default` instead of raising.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "it = iter([10, 20])\nprint(next(it), next(it))\nprint(next(it, \"done\"))",
  "answer": "10 20\ndone",
  "explanation": "Two next() calls take both items. The third call has nothing left, so instead of raising StopIteration it returns the default you passed." }
```

## 2. Iterable vs iterator: the single-pass gotcha

Two different things take part:

- An **iterable** is something you can *ask* for an iterator: a list, a dict, a string. Every `iter(my_list)` gives a **new** iterator that starts at the beginning, so you can loop over a list as often as you like.
- An **iterator** is the cursor itself. It only moves forward. `iter(iterator)` returns *the same object*, so a second loop continues from where the first stopped, which after a full pass means **nothing at all, and no error**.

`map()`, `filter()`, `zip()`, open files and generators are iterators:

```python
prices = ["12", "5", "30"]
amounts = map(int, prices)     # an iterator, not a list
print(sum(amounts))
print(sum(amounts))            # second pass: already exhausted
print(iter(prices) is prices, iter(amounts) is amounts)
```

```console
47
0
False True
```

The second `sum` silently got an empty stream. That is the classic bug: a function "validates" its input with one pass (`if not any(...)`, `len(list(rows))`, a debug `print(list(rows))`) and then the real loop sees nothing. Go's closest equivalent is a channel: once you've received every value, ranging over it again gives you nothing.

**Fix:** if you need two passes, either make a list once (`amounts = list(map(int, prices))`) or recreate the iterator. Don't make a list "just in case": the point of an iterator is that it doesn't hold everything in memory.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "squares = (n * n for n in range(4))\nprint(list(squares))\nprint(list(squares))",
  "answer": "[0, 1, 4, 9]\n[]",
  "explanation": "The parentheses make a generator expression, which is an iterator. The first list() consumes it; the second finds it exhausted and builds an empty list. With square brackets (a list comprehension) both lines would print [0, 1, 4, 9]." }
```

```quiz
{ "id": "q3", "type": "choice", "label": "Debugging",
  "prompt": "`def report(rows):` first does `print(\"rows:\", list(rows))` for debugging, then `for r in rows: total += r`. Called with a list, total is right. Called with `rows = (int(x) for x in data)`, total is always 0. Why?",
  "options": ["The debug list() consumed the generator, so the loop gets an exhausted iterator", "Generators can't be passed to functions", "int() returns strings inside a generator", "print() resets the generator to the end"], "answer": 0,
  "explanation": "A list is an iterable: each loop gets a fresh iterator. A generator is a single-pass iterator: list(rows) used it up, and the for loop silently saw no items." }
```

## 3. Generators: functions that pause

Writing an iterator class by hand (`__iter__` returning `self`, `__next__` raising `StopIteration`) works but is tedious. A **generator function** does the same with `yield`. Any function that contains `yield` is a generator function, and calling it does **not run the body**. It returns a generator object. Each `next()` runs the body until the next `yield`, hands that value out and **pauses there**, keeping all local variables. When the body ends, the generator raises `StopIteration` for you.

```python
def countdown(n):
    print("  (starting)")
    while n > 0:
        yield n
        n -= 1
    print("  (finished)")


c = countdown(2)
print(type(c).__name__)
print(next(c))
print(next(c))
print(next(c, "no more"))
print(list(countdown(3)))
```

```console
generator
  (starting)
2
1
  (finished)
no more
  (starting)
  (finished)
[3, 2, 1]
```

Notice that `(starting)` appears only at the first `next()`, not when `countdown(2)` is called, and `(finished)` only when someone asks for a value after the last one.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "def steps():\n    print(\"start\")\n    yield 1\n    print(\"middle\")\n    yield 2\n    print(\"end\")\n\ng = steps()\nprint(\"created\")\nprint(next(g))\nprint(next(g))",
  "answer": "created\nstart\n1\nmiddle\n2",
  "explanation": "Calling steps() runs nothing, so 'created' comes first. Each next() runs up to the next yield and pauses. 'end' is never printed: nobody asked for a third value, so the generator stays paused after yield 2." }
```

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "If a generator function contains `return` after a few `yield`s, the returned value is produced as the last item of the loop.", "answer": false,
  "explanation": "return inside a generator just ends the iteration (the caller sees StopIteration). A value after return is not yielded, so a for loop or list() never sees it." }
```

## 4. The Go comparison: pull vs push

Before Go 1.23, a Go "iterator" was usually a closure that returns the next value and an `ok` flag. Run with Go 1.21:

```go
// countdown returns a "next" function: each call gives the next value and ok=false at the end.
func countdown(n int) func() (int, bool) {
	return func() (int, bool) {
		if n == 0 {
			return 0, false
		}
		n--
		return n + 1, true
	}
}

func main() {
	next := countdown(3)
	for v, ok := next(); ok; v, ok = next() {
		fmt.Println(v)
	}
	_, ok := next()
	fmt.Println("after the end:", ok)
}
```

```console
3
2
1
after the end: false
```

That is exactly a Python iterator: **pull-style** (the caller asks for each value), state kept between calls (here in the captured `n`; in Python, in the paused generator), and single-pass (after the end it keeps saying "no more", just as `__next__` must keep raising `StopIteration`). The Python generator just lets you write the producer as a straight loop instead of a state machine.

Go 1.23 added range-over-func with the `iter` package: `iter.Seq[V]` is `func(yield func(V) bool)`. That style is **push**: the iterator function calls `yield(v)` for each value and stops early if `yield` returns `false`. Same word `yield`, opposite direction of control. In Python, the generator is paused and the consumer drives it with `next()`.

```quiz
{ "id": "q8", "type": "truefalse",
  "prompt": "With a Go 1.23 `iter.Seq`, the loop pulls each value by calling a next function, just like Python's `next()` on a generator.", "answer": false,
  "explanation": "iter.Seq is push-style: the iterator function calls yield(v) for every value and the loop body runs inside that callback. Python generators are pull-style: the consumer calls next(), and the generator runs until its next yield." }
```

## 5. Pipelines: one item at a time

Generators chain: each stage loops over the previous one and yields to the next. Nothing runs until the last stage is asked for a value, and then **each item travels through the whole pipeline before the next one is read**:

```python
def read_amounts(lines):
    for line in lines:
        print(f"  read {line!r}")
        name, amount = line.split(",")
        yield int(amount)


def at_least(amounts, minimum):
    for amount in amounts:
        if amount >= minimum:
            yield amount


orders = ["tea,4", "laptop,900", "pen,2", "desk,250"]
big = at_least(read_amounts(orders), 100)
print("nothing read yet")
print(next(big))
print("total of the rest:", sum(big))
```

```console
nothing read yet
  read 'tea,4'
  read 'laptop,900'
900
  read 'pen,2'
  read 'desk,250'
total of the rest: 250
```

Getting the first big order read exactly two lines: `tea` was read and dropped, `laptop` passed. Replace `orders` with an open 2 GB file (a file is an iterator over its lines) and memory use stays the same, because only one line is alive at a time. With lists at each stage, every stage would hold the whole file.

Why this design helps with your known weak spot (edge cases): each stage is a tiny function you can test alone with a 3-item list, including the empty list.

```quiz
{ "id": "q6", "type": "output",
  "prompt": "What does this print?",
  "code": "def nums():\n    for n in [1, 2, 3, 4]:\n        print(\"pull\", n)\n        yield n\n\nevens = (n for n in nums() if n % 2 == 0)\nprint(next(evens))",
  "answer": "pull 1\npull 2\n2",
  "explanation": "next(evens) pulls from nums() until the filter finds an even number: 1 is pulled and dropped, 2 is pulled and returned. 3 and 4 are never pulled." }
```

## 6. Common mistakes and limits

- **Building a list and calling it a generator.** `result.append(x)` then `return result` is eager: all work happens on the call, and the whole result sits in memory. Use `yield x`.
- **`len()` and indexing don't work** on generators: there is no length until you've consumed them.

```python
squares = (n * n for n in range(5))
try:
    print(len(squares))
except TypeError as e:
    print("TypeError:", e)
print(sum(1 for _ in squares))
```

```console
TypeError: object of type 'generator' has no len()
5
```

- **Reusing an exhausted iterator** (section 2). If a function needs two passes, say so in its contract and take a list.
- **Checking a limit after the loop already pulled the item.** The `for` statement calls `next()` *before* your loop body runs. If you decide inside the body that you've had enough, that item has already been taken from the source. On a shared stream (a file, a socket) it is gone for the next reader.
- **When not to use a generator:** small data you need several times, need to index, or need to sort. A list is simpler then.

```quiz
{ "id": "q7", "type": "choice",
  "prompt": "A function must read a log file of several GB and return the number of ERROR lines. Which approach keeps memory flat?",
  "options": ["`lines = f.readlines()` then loop over `lines`", "`sum(1 for line in f if line.startswith(\"ERROR\"))`", "`len([line for line in f if line.startswith(\"ERROR\")])`", "`lines = list(f)` then `lines.count(...)`"], "answer": 1,
  "explanation": "The generator expression pulls one line at a time from the file iterator and keeps only a running total. readlines(), list(f) and the list comprehension all hold every (matching) line in memory first." }
```

## 7. Your turn

The exercise is a three-stage log pipeline. The tests check laziness: they feed an **endless** log and count how many lines your code pulls, so a stage that builds a list fails. Watch the edge cases from sections 2 and 6.

```exercise
PY.M07.L01.E1
```
