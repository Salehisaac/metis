---
{ "id": "PY.M07.A", "module": "PY.M07", "title": "PY.M07 module assessment: iterators, generators, context managers, decorators", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before moving on.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?",
  "code": "words = [\"go\", \"py\", \"rust\"]\nlong_words = filter(lambda w: len(w) > 2, words)\nprint(list(long_words), list(long_words), len(words))",
  "answer": "['rust'] [] 3",
  "explanation": "filter() returns a single-pass iterator: the first list() consumes it and the second finds it exhausted. The list words itself is untouched." }
```

```quiz
{ "id": "a2", "type": "truefalse",
  "prompt": "Calling a generator function runs its body up to the first `yield`.", "answer": false,
  "explanation": "Calling it only creates the generator object. The body starts running on the first next() (or the first step of a for loop)." }
```

```quiz
{ "id": "a3", "type": "output",
  "prompt": "What does this print?",
  "code": "from contextlib import contextmanager\n\n@contextmanager\ndef tx():\n    print(\"begin\")\n    try:\n        yield\n        print(\"commit\")\n    except Exception:\n        print(\"rollback\")\n        raise\n\ntry:\n    with tx():\n        print(\"insert\")\n        raise ValueError(\"duplicate\")\nexcept ValueError:\n    print(\"handled\")",
  "answer": "begin\ninsert\nrollback\nhandled",
  "explanation": "The ValueError is re-raised inside the generator at the yield, so 'commit' is skipped and the except block runs. It re-raises, so the caller's except prints 'handled'." }
```

```quiz
{ "id": "a4", "type": "output",
  "prompt": "What does this print?",
  "code": "adders = [lambda x: x + n for n in range(3)]\nprint([f(10) for f in adders])",
  "answer": "[12, 12, 12]",
  "explanation": "Late binding: each lambda looks up n when it's called, after the loop has finished with n == 2. Bind the value with a default argument: lambda x, n=n: x + n." }
```

```quiz
{ "id": "a5", "type": "choice",
  "prompt": "Why do you put `@functools.wraps(func)` on the wrapper inside a decorator?",
  "options": ["So the decorated function keeps its own __name__ and __doc__ (and gets __wrapped__)", "So the wrapper runs faster", "So exceptions inside func are caught", "So the decorator runs only once"], "answer": 0,
  "explanation": "Without wraps, the decorated function reports the wrapper's name and loses its docstring, which shows up in tracebacks, logs and tools." }
```

```quiz
{ "id": "a6", "type": "output",
  "prompt": "What does this print?",
  "code": "def tag(name):\n    print(\"tag\", name)\n    def deco(func):\n        print(\"deco\", name)\n        return func\n    return deco\n\n@tag(\"a\")\n@tag(\"b\")\ndef f():\n    pass\n\nprint(\"ready\")",
  "answer": "tag a\ntag b\ndeco b\ndeco a\nready",
  "explanation": "The decorator expressions tag(\"a\") and tag(\"b\") are evaluated top to bottom when def runs, then the resulting decorators are applied bottom-up: f = deco_a(deco_b(f)). All of it happens before 'ready'." }
```
