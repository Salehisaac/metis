---
{ "id": "PY.M01.A", "module": "PY.M01", "title": "PY.M01 module assessment: running Python, environments, pytest", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before PY.M02.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?", "code": "# python3 -c 'import sys; print(len(sys.argv))' a b",
  "answer": "3",
  "explanation": "argv is ['-c', 'a', 'b']: '-c' takes the place of the script name, then the two arguments." }
```

```quiz
{ "id": "a2", "type": "choice",
  "prompt": "`pip install requests` succeeded, but `python3 app.py` fails with ModuleNotFoundError: No module named 'requests'. What's the most likely cause?",
  "options": ["pip and python3 belong to different environments", "The package name is case-sensitive", "Python caches failed imports", "app.py must be inside site-packages"], "answer": 0,
  "explanation": "A bare pip can belong to a different interpreter than python3. Use .venv/bin/python -m pip so both use the same environment." }
```

```quiz
{ "id": "a3", "type": "truefalse",
  "prompt": "Code inside `if __name__ == \"__main__\":` runs when another module imports the file.", "answer": false,
  "explanation": "On import, __name__ is the module's own name, so the guarded block is skipped. It runs only when the file is the program you started." }
```

```quiz
{ "id": "a4", "type": "output",
  "prompt": "What does this print?", "code": "print(\"a  b\".split())",
  "answer": "['a', 'b']",
  "explanation": "split() with no argument splits on runs of whitespace, so no empty strings appear. split(\" \") would give ['a', '', 'b']." }
```

```quiz
{ "id": "a5", "type": "choice",
  "prompt": "pytest shows `E  AssertionError: assert 1 == 0` and `+  where 1 = count_words('')`. What does that tell you?",
  "options": ["count_words('') returned 1, but the test expected 0", "The test function returned 1", "pytest crashed while collecting", "One test ran and zero failed"], "answer": 0,
  "explanation": "In `assert X == Y` the left side is what the code produced and the right side is what the test expected. The 'where' line names the call." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "A teammate commits their .venv folder 'so everyone has the same packages'. What do you suggest instead, and why?",
  "model": "Don't commit .venv: it's machine-specific and disposable, and it breaks when moved. Commit requirements.txt (from pip freeze) and have everyone run python3 -m venv .venv, then .venv/bin/python -m pip install -r requirements.txt. Add .venv/ to .gitignore.",
  "explanation": "Commit the recipe, not the environment." }
```
