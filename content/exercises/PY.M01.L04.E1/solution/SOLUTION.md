```gitignore
# Virtual environments
.venv/

# Python bytecode caches
__pycache__/
*.pyc

# pytest
.pytest_cache/
result.xml
```

**Why each line**

- **`.venv/`**: the trailing slash means directories only. No slash in the middle, so it matches at any depth, including a `.venv/` inside an exercise folder.
- **`__pycache__/` and `*.pyc`**: Python writes compiled bytecode caches next to imported modules. They're regenerated on every run and differ between Python versions.
- **`.pytest_cache/`**: pytest's state, such as which tests failed last time (`--lf`).
- **`result.xml`**: the JUnit report your exercise runs write. It's an output, not source.

**Debugging tip:** `git check-ignore -v PATH` prints which line of which `.gitignore` matched. Remember that `.gitignore` never untracks a file that's already committed; for that, use `git rm --cached FILE`.
