---
{
  "id": "PY.M01.L01",
  "title": "Running Python: interpreter, REPL, scripts, python -m",
  "difficulty": "beginner",
  "minutes": 35,
  "prerequisites": [],
  "objectives": [
    "Run Python code four ways: the REPL, a script file, python -c and python -m",
    "Explain why the REPL shows a value but a script doesn't, and what repr vs print output looks like",
    "Read command-line arguments from sys.argv and exit with a status code via sys.exit",
    "Make a file both importable and runnable with if __name__ == \"__main__\""
  ],
  "why": "Every later lesson, exercise and FastAPI app starts with running Python correctly. The __main__ guard in particular is how real tools stay importable for tests while still working from the command line.",
  "applications": [
    "Small CLI tools and scripts that tests can import",
    "Running tools from your environment: python -m pip, python -m pytest, python -m venv",
    "Exit codes that shells, CI pipelines and Docker health checks understand"
  ],
  "exercises": ["PY.M01.L01.E1"],
  "sources": [
    {
      "title": "Python Tutorial: Using the Python Interpreter",
      "url": "https://docs.python.org/3.12/tutorial/interpreter.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Interactive prompts >>> and ...", "sys.argv holds the script name and arguments; argv[0] is '-c' with -c", "python -m module runs a module as a script"]
    },
    {
      "title": "Command line and environment",
      "url": "https://docs.python.org/3.12/using/cmdline.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["-m searches sys.path for the module and runs it as __main__", "Script: the script's directory goes first on sys.path; -m and -c: the current directory", "-i enters interactive mode after running"]
    },
    {
      "title": "__main__: Top-level code environment",
      "url": "https://docs.python.org/3.12/library/__main__.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["__name__ is '__main__' in the top-level environment", "Code under if __name__ == '__main__' doesn't run on import", "Put behaviour in main() and call sys.exit(main())"]
    },
    {
      "title": "sys: System-specific parameters and functions",
      "url": "https://docs.python.org/3.12/library/sys.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["sys.exit(int): 0 success, non-zero failure", "sys.exit with a non-int object prints it to stderr and exits with 1", "sys.argv[0] is the script name"]
    }
  ]
}
---
## 1. No build step

In Go you compile, then run (`go run` just hides the build). Python has no separate build: `python3` reads your source and runs it **top to bottom**. Every statement at the top level of a file executes when the file runs, *or when it is imported*. Go also runs package-level initialisers and `init()` on import, but Go only allows declarations at package level. In Python *any* statement there runs on import, including `print` calls and argument parsing. Section 4 is about why that matters.

On this machine the interpreter is `python3` (3.12). Inside a virtual environment (next lesson) it's also available as `python`.

## 2. The REPL: for poking at things

Run `python3` with no arguments and you get the interactive prompt (the REPL):

```console
$ python3
>>> 2 ** 10
1024
>>> "go" * 3
'gogogo'
>>> print("go" * 3)
gogogo
```

Two things to notice:

- **The REPL echoes the value of each expression.** A script never does that. In a file, only `print()` produces output.
- The echo shows the value's **repr** (a developer view, here with quotes), while `print` shows the plain text. `'gogogo'` and `gogogo` are the same string displayed two ways. Go has the same split: `%q` vs `%s`.

Use the REPL to check how something behaves before you rely on it, the way you might write a throwaway `main.go`. Quit with `exit()` or Ctrl+D.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "bare.py contains two lines: `x = 2 ** 10` and then `x` on its own. What does `python3 bare.py` print?",
  "options": ["1024", "Nothing", "x = 1024", "An error"], "answer": 1,
  "explanation": "Only the REPL echoes expression values. In a script, a bare `x` is evaluated and thrown away; you need print(x)." }
```

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "In the REPL, typing `\"go\" * 3` shows exactly the same text as `print(\"go\" * 3)`.", "answer": false,
  "explanation": "The REPL shows the repr, 'gogogo' (with quotes). print shows gogogo. Same value, different display." }
```

## 3. Scripts and command-line arguments

A script is a `.py` file you pass to the interpreter. Its arguments arrive in `sys.argv`, a list of strings. That's Go's `os.Args`, and `sys.argv[0]` is the script name, just like `os.Args[0]`.

```python
# greet.py
import sys

print("argv:", sys.argv)
print(f"hello, {sys.argv[1]}")
```

```console
$ python3 greet.py Ali
argv: ['greet.py', 'Ali']
hello, Ali
$ python3 greet.py
argv: ['greet.py']
Traceback (most recent call last):
  File "greet.py", line 4, in <module>
    print(f"hello, {sys.argv[1]}")
                    ~~~~~~~~^^^
IndexError: list index out of range
```

The second run crashed with exit status 1, and the traceback names the line. Read tracebacks **bottom-up**: the last line is the error, and the lines above show where it happened.

To fail on purpose with a clear message, write to **stderr** and exit with a non-zero status. In Go that's `fmt.Fprintln(os.Stderr, ...)` and `os.Exit(2)`:

```python
import sys

print("usage: python3 greet.py NAME", file=sys.stderr)
sys.exit(2)
```

`sys.exit(0)` (or `sys.exit()`) means success. Any other integer means failure, and shells and CI check this number. A common mistake is `sys.exit("message")`: it prints the message to stderr and always exits with 1. That's fine for a quick abort, but you can't choose the code.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?", "code": "# run as:  python3 -c 'import sys; print(sys.argv)'",
  "answer": "['-c']", "accept": ["[\"-c\"]"],
  "explanation": "With -c there is no script file, so argv[0] is the string '-c'." }
```

## 4. Import runs the file, so guard your entry point

`import tool` **executes tool.py top to bottom**, once, and then gives you the module. Every module has a `__name__`:

- When imported, `__name__` is the module's name (`"tool"`).
- When it's the program you started (script, `-m`, `-c`, REPL), `__name__` is `"__main__"`.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "tool.py contains `print(__name__)`. main.py contains `import tool` then `print(__name__)`. What does `python3 main.py` print?",
  "answer": "tool\n__main__",
  "explanation": "Importing tool runs tool.py, which prints its name, tool. Then main.py, the program you started, prints __main__." }
```

That's why real scripts look like this:

```python
# shout.py
import sys


def shout(text: str) -> str:
    return text.upper() + "!"


def main() -> int:
    for word in sys.argv[1:]:
        print(shout(word))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

```console
$ python3 shout.py go py
GO!
PY!
$ python3 -c 'import shout; print(shout.shout("hi"))'
HI!
```

- **Run it:** `__name__ == "__main__"`, so `main` runs and its return value becomes the exit code.
- **Import it:** nothing runs. The import prints nothing, and you just get `shout` and `main` to call.

This is the Go split between `package main` and a library, but in one file. Keep the guarded block tiny: put the work in `main()`, as the official docs recommend.

**Common mistake:** putting `print(...)` or argument parsing at the top level. Every importer, including pytest, then runs it.

## 5. `python -m`: run a module by name

`python3 -m NAME` finds the module `NAME` on the import path and runs it as `__main__`. You'll use it constantly:

```console
$ echo '{"name": "ali", "langs": ["go", "py"]}' | python3 -m json.tool
{
    "name": "ali",
    "langs": [
        "go",
        "py"
    ]
}
$ python3 -m http.server 8765      # how this academy's site is served
```

`python3 -m pip`, `python3 -m pytest` and `python3 -m venv` work the same way. The big benefit is that **`-m` uses the modules of exactly that interpreter.** A bare `pip` command is whichever `pip` comes first on your PATH, and it may belong to a different Python. The next lesson is about why that matters.

A small difference: a script puts **its own directory** first on the import path, while `-m` and `-c` put the **current directory** first. That's why `python3 -m tool` works from the folder that contains `tool.py`.

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "From the folder containing tool.py (which has `print(__name__)`), you run `python3 -m tool`. What does it print?",
  "options": ["tool", "__main__", "tool.py", "-m"], "answer": 1,
  "explanation": "-m runs the module as the top-level program, so its __name__ is __main__, exactly as with python3 tool.py." }
```

```quiz
{ "id": "q5", "type": "explain", "label": "Application",
  "prompt": "Your colleague's CI step runs `pip install -r requirements.txt` and then `python3 app.py` fails with ModuleNotFoundError. What would you change, and why?",
  "model": "Use the same interpreter for both: `python3 -m pip install -r requirements.txt`, or better the venv's own interpreter. A bare `pip` may belong to a different Python than `python3`.",
  "explanation": "`python -m pip` ties pip to that exact interpreter." }
```

## 6. Your turn

Every exercise in this academy uses the same loop. Run these from the academy's project folder:

```console
$ .venv/bin/python tools/scaffold.py PY.M01.L01.E1   # once: copies the starter files
created workspace/PY.M01.L01.E1
$ cd workspace/PY.M01.L01.E1
$ ../../.venv/bin/pytest                           # run the tests (writes result.xml)
```

You'll learn what `.venv` and `pytest` are in the next two lessons; for now these three commands are enough. Edit the file, rerun pytest until it's green, then import `result.xml` on the exercise below as evidence.

The exercise is a **refactor**: the script works from the shell but runs its code on import. Use what you learned in sections 3 and 4.

```exercise
PY.M01.L01.E1
```
