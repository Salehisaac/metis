**New file `settings.py`**

```python
CURRENCY = "EUR"
```

**`__main__.py`**

```python
import sys

from .cli import main

sys.exit(main(sys.argv[1:]))
```

**Import changes**

- `ledger.py`: `from report import CURRENCY` becomes `from .settings import CURRENCY`
- `report.py`: `from ledger import describe, load` becomes `from .ledger import describe, load`, and the `CURRENCY = "EUR"` line moves to settings.py
- `cli.py`: `from report import render` becomes `from .report import render`

**Why each step**

1. **Absolute → relative.** `from report import ...` searches `sys.path` for a *top-level* module called `report`. When you run `python -m spend` from the parent folder, `sys.path[0]` is that parent folder, not `spend/`, so you get `ModuleNotFoundError: No module named 'report'`. A relative import (`.report`) means "the module `report` in *my* package", whatever the package is called. That's why the `budget` test passes too. (`from spend.report import ...` would also work under the name spend, but fails after the rename.)
2. **The cycle.** Importing `spend.ledger` starts running ledger.py. Its first line imports report, which starts running report.py, whose first line needs `describe` from ledger. ledger is already in `sys.modules` but has only run its first line, so `describe` doesn't exist yet: `cannot import name 'describe' from partially initialized module`. Moving the shared constant into a module that imports nothing from the package turns the cycle into a one-way chain: cli → report → ledger → settings.
3. **`__main__.py`.** `python -m spend` runs `spend/__main__.py` with `__name__ == "__main__"`. It stays tiny and needs no `if __name__` guard (the `__main__` docs recommend this). `sys.exit(main(...))` turns main's return value into the process exit status. Without `sys.exit`, `python -m spend` with no argument would print the usage message but still exit 0, and scripts or CI couldn't tell it failed.

**Alternatives**

- Put `CURRENCY` in ledger.py, since ledger is the module that uses it. That works too: report then imports only from ledger.
- An import inside `describe()` also hides the cycle, because it runs at call time, when both modules are fully loaded. It's a last resort: the cycle is still there, and the next top-level import can bring the error back.
- `from . import report` plus `report.CURRENCY` inside the function only works for some import orders. If the other module still uses `from .x import name`, the error comes back as soon as the entry point changes.
