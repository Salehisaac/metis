---
{
  "id": "PY.M01.L01",
  "title": "Running Python: interpreter, REPL, scripts, python -m",
  "difficulty": "beginner",
  "minutes": 25,
  "prerequisites": [],
  "objectives": ["FIXTURE objective one", "FIXTURE objective two"],
  "why": "FIXTURE: engine test content, not a real lesson.",
  "applications": ["FIXTURE application"],
  "exercises": ["PY.M01.L01.E1"],
  "sources": [
    {
      "title": "Using the Python Interpreter",
      "url": "https://docs.python.org/3/tutorial/interpreter.html",
      "version": "3.12",
      "verified": "2026-11-12",
      "claims": ["FIXTURE claim"]
    }
  ]
}
---
## Fixture lesson

This is **fixture** content for engine tests. It has `inline code` and a [safe link](#/courses).

```python
def greet(name: str) -> str:
    return f"hi {name}"
```

```go
func main() { fmt.Println("hi") }
```

```unknownlang
plain text, must not be highlighted or warn
```

### Hostile input (must be neutralised)

<script>window.__xss = "script"</script>
<img src="data:," onerror="window.__xss = 'img'">
<iframe src="javascript:window.__xss='iframe'"></iframe>

[bad link](javascript:window.__xss='link')

### Quizzes

```quiz
{ "id": "q1", "type": "choice", "prompt": "Which prints a list? <b>not bold</b>",
  "options": ["print([1, 2])", "print(1, 2)"], "answer": 0,
  "explanation": "A list literal prints with brackets." }
```

```quiz
{ "id": "q2", "type": "truefalse", "prompt": "Assignment copies a list.", "answer": false,
  "explanation": "Assignment binds another name to the same object." }
```

```quiz
{ "id": "q3", "type": "output", "prompt": "What does this print?", "code": "print([1, 2] + [3])",
  "answer": "[1, 2, 3]", "accept": ["[1,2,3]"], "explanation": "+ builds a new list." }
```

```quiz
{ "id": "q4", "type": "explain", "prompt": "Why does a slice past the end not raise?",
  "model": "Slices clamp their bounds; only single indexing raises IndexError.",
  "explanation": "Compare a[1:100] with a[100]." }
```

### Exercise

```exercise
PY.M01.L01.E1
```
