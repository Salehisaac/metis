---
{
  "id": "DB.M04.L03",
  "title": "A tested repository layer",
  "difficulty": "intermediate",
  "minutes": 75,
  "prerequisites": ["DB.M04.L02"],
  "objectives": [
    "Explain what a repository is responsible for: SQL in one place, domain objects out, domain errors instead of driver errors, one transaction per write",
    "Translate only the database errors callers care about (a UNIQUE violation) into domain exceptions, chained with raise ... from, and let the others through",
    "Implement keyset pagination and explain why it beats OFFSET for a growing table",
    "Test a repository with a fresh in-memory database per test (a pytest fixture), covering results, errors, and transaction state"
  ],
  "why": "Up to now, SQL has lived in loose strings and functions. A real service keeps it behind a small interface, so handlers never see tuples or sqlite3 exceptions, and so the rules (placeholders, transactions, error translation) are implemented once and tested once. Your Go services have the same split between handlers and a data-access layer. PRJ-02, the message store, is built this way, and this lesson's exercise is its warm-up on the users table.",
  "applications": [
    "The data-access layer of a FastAPI service (WEB modules) and of PRJ-02",
    "Turning 'duplicate key' into a 409 Conflict at the API boundary",
    "Infinite-scroll lists with keyset pagination"
  ],
  "exercises": ["DB.M04.L03.E1"],
  "sources": [
    {
      "title": "sqlite3: DB-API 2.0 interface for SQLite databases",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["sqlite3.Error has sqlite_errorcode and sqlite_errorname (added in 3.11)", "IntegrityError is raised when relational integrity is affected", "The connection context manager commits on success and rolls back on an exception, which is still raised", "lastrowid is the row id of the last inserted row"]
    },
    {
      "title": "pytest: How to use fixtures",
      "url": "https://docs.pytest.org/en/stable/how-to/fixtures.html",
      "version": "pytest stable docs (9.x); verified locally with pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": ["Tests request fixtures by declaring them as arguments", "Fixtures are functions decorated with @pytest.fixture", "With the default function scope each test gets its own fixture result"]
    },
    {
      "title": "SQLite: SELECT (LIMIT/OFFSET)",
      "url": "https://www.sqlite.org/lang_select.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["With OFFSET, the first M rows are omitted from the result set returned and the next N rows are returned"]
    }
  ]
}
---
## 1. What a repository is for

A **repository** is a class that owns all the SQL for one kind of thing. Callers ask it in domain terms ("create product MUG-1", "find product 7") and get domain answers: dataclass objects, `None`, or a domain exception. In Go terms, it's the data-access layer your handlers call instead of `db.Query`.

It's responsible for four things:

1. **SQL, with placeholders,** in one place, so it can be reviewed and changed in one place.
2. **Rows → objects.** Callers never see tuples.
3. **Driver errors → domain errors,** but only the ones callers can act on.
4. **One transaction per write method,** so each call is all or nothing (DB.M03).

It is *not* responsible for HTTP status codes, input parsing or business workflows that span several repositories. Those live one layer up.

```python
# catalog.py
import sqlite3
from dataclasses import dataclass

SCHEMA = """
CREATE TABLE products (
    id    INTEGER PRIMARY KEY,
    sku   TEXT NOT NULL UNIQUE,
    price INTEGER NOT NULL CHECK (price >= 0)
);
"""


@dataclass(frozen=True)
class Product:
    id: int
    sku: str
    price: int


class SkuTaken(Exception):
    pass


class ProductMissing(Exception):
    pass


class ProductRepository:
    def __init__(self, db):
        self.db = db

    def create(self, sku, price):
        try:
            with self.db:
                cur = self.db.execute("INSERT INTO products (sku, price) VALUES (?, ?)", (sku, price))
        except sqlite3.IntegrityError as exc:
            if exc.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE":
                raise SkuTaken(sku) from exc
            raise
        return Product(cur.lastrowid, sku, price)

    def find(self, product_id):
        row = self.db.execute("SELECT id, sku, price FROM products WHERE id = ?", (product_id,)).fetchone()
        return Product(*row) if row else None

    def change_price(self, product_id, price):
        with self.db:
            cur = self.db.execute("UPDATE products SET price = ? WHERE id = ?", (price, product_id))
            if cur.rowcount != 1:
                raise ProductMissing(product_id)
```

The connection is **passed in** (composition, as in PY.M05.L04), not created inside. Tests can hand it an in-memory database; the app hands it a file database.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Where should 'a duplicate SKU becomes HTTP 409 Conflict' live?",
  "options": ["In the repository: it returns 409", "In the HTTP handler: the repository raises SkuTaken, the handler maps it to 409", "In the database, with a trigger", "In the dataclass"], "answer": 1,
  "explanation": "The repository speaks domain language (SkuTaken); HTTP is the handler's business. The same repository then works for a CLI or a background job." }
```

## 2. Translate errors narrowly

`IntegrityError` covers every constraint: UNIQUE, NOT NULL, CHECK, FOREIGN KEY. Only the UNIQUE one means "SKU taken"; the others mean a bug in the caller or the repository, and hiding them behind `SkuTaken` would send you debugging in the wrong place. Since Python 3.11, sqlite3 errors carry `sqlite_errorname`, the SQLite error code's name:

```python
db = sqlite3.connect(":memory:")
db.executescript(SCHEMA)
repo = ProductRepository(db)
print(repo.create("MUG-1", 8))
try:
    repo.create("MUG-1", 9)
except SkuTaken as e:
    print("SkuTaken:", e, "| cause:", type(e.__cause__).__name__)
try:
    repo.create("PEN-1", -1)
except sqlite3.IntegrityError as e:
    print("IntegrityError:", e)
```

```text
Product(id=1, sku='MUG-1', price=8)
SkuTaken: MUG-1 | cause: IntegrityError
IntegrityError: CHECK constraint failed: price >= 0
```

- `raise SkuTaken(sku) from exc` keeps the original error as `__cause__`, like wrapping with `%w` in Go (PY.M04.L02). A traceback shows both.
- The `except` is **outside** the `with` block: by the time it runs, the block has already rolled back, so the caller gets a clean connection.
- The negative price is not translated: it's a programming error, and it surfaces as one.

**Why not check first with a SELECT?** "Is MUG-1 free? Then insert" has a gap between the two statements: two requests can both see "free". The UNIQUE constraint can't be raced; the repository's job is to translate its error.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute('CREATE TABLE t(email TEXT UNIQUE NOT NULL)')\nc.execute(\"INSERT INTO t VALUES ('a@x')\")\nfor v in ['a@x', None]:\n    try:\n        c.execute('INSERT INTO t VALUES (?)', (v,))\n    except sqlite3.IntegrityError as e:\n        print(e.sqlite_errorname)",
  "answer": "SQLITE_CONSTRAINT_UNIQUE\nSQLITE_CONSTRAINT_NOTNULL",
  "explanation": "Both are IntegrityError, but the error name tells a duplicate apart from a missing value." }
```

## 3. Keyset pagination

DB.M01 paged with `LIMIT ? OFFSET ?`. Two problems for a list people scroll through:

- **It shifts.** If a row is inserted before the current page between two requests, every later row moves down by one: the user sees one item twice. A deleted row makes one disappear.
- **It re-reads.** `OFFSET 10000` still produces the first 10,000 rows of the sorted result, only to throw them away.

**Keyset pagination** remembers where the last page ended and continues from there: `WHERE sku > ? ORDER BY sku LIMIT ?`, passing the last SKU the caller saw. New rows before that point don't shift anything, and with an index on the sort column (DB.M05) the database can jump straight to the start. The sort key must be unique (or made unique with a tie-break column), or rows sharing a key can be skipped at a page boundary.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "Page 1 (size 2) was read, then 'apple' was inserted. What does each method return as page 2?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute('CREATE TABLE tags(name TEXT PRIMARY KEY)')\nc.executemany('INSERT INTO tags VALUES (?)', [('bug',), ('docs',), ('perf',), ('ui',)])\npage1 = [r[0] for r in c.execute('SELECT name FROM tags ORDER BY name LIMIT 2')]\nc.execute(\"INSERT INTO tags VALUES ('apple')\")\nprint(c.execute('SELECT name FROM tags ORDER BY name LIMIT 2 OFFSET 2').fetchall())\nprint(c.execute('SELECT name FROM tags WHERE name > ? ORDER BY name LIMIT 2', (page1[-1],)).fetchall())",
  "answer": "[('docs',), ('perf',)]\n[('perf',), ('ui',)]",
  "explanation": "Page 1 was bug, docs. With OFFSET, the new 'apple' shifts everything, so docs appears again. Keyset continues after 'docs'." }
```

## 4. Testing the repository

Repository tests check the **contract**: what comes back, which exception, what's committed. They don't check the SQL text. Each test needs a fresh database, and a **pytest fixture** provides one: a function marked `@pytest.fixture`, which pytest runs and passes to every test that names it as a parameter (the same mechanism as `tmp_path`). Each test gets its own result.

```python
# test_catalog.py
import sqlite3

import pytest

from catalog import SCHEMA, Product, ProductMissing, ProductRepository, SkuTaken


@pytest.fixture
def repo():
    db = sqlite3.connect(":memory:")
    db.executescript(SCHEMA)
    return ProductRepository(db)


def test_create_and_find(repo):
    created = repo.create("MUG-1", 8)
    assert created == Product(1, "MUG-1", 8)
    assert repo.find(1) == created
    assert repo.find(2) is None


def test_duplicate_sku(repo):
    repo.create("MUG-1", 8)
    with pytest.raises(SkuTaken) as info:
        repo.create("MUG-1", 9)
    assert isinstance(info.value.__cause__, sqlite3.IntegrityError)
    assert repo.db.in_transaction is False


def test_negative_price_is_not_a_duplicate(repo):
    with pytest.raises(sqlite3.IntegrityError):
        repo.create("PEN-1", -1)


def test_change_price_of_missing_product(repo):
    with pytest.raises(ProductMissing):
        repo.change_price(42, 10)
```

```text
$ pytest -q test_catalog.py
....                                                                     [100%]
4 passed in 0.01s
```

What these cover, and why each matters:

- the happy path, **and** "not found" returning `None` (not an exception, not a tuple)
- the error translation, **and** its cause chain, **and** a clean connection afterwards (`in_transaction`)
- a *non*-translation: the CHECK failure must not become `SkuTaken`
- a write on a missing row

For a committed-or-not check you'd add a file database and a second connection, exactly as in DB.M03.L03. (The exercise's tests build the repository inside each test instead of in a fixture, so an unfinished `__init__` shows up as a test failure, not a setup error.)

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "Two tests that both take the `repo` fixture above share one in-memory database, so a product created in the first test is visible in the second.", "answer": false,
  "explanation": "A function-scoped fixture (the default) runs again for every test, so each test gets a new connection to a new in-memory database." }
```

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "A repository method catches `sqlite3.IntegrityError` and always raises `EmailTaken`. A caller passes `None` as the email. What does the caller see?",
  "options": ["IntegrityError: NOT NULL constraint failed", "EmailTaken, which is misleading: the real problem is the missing value", "None", "ValueError"], "answer": 1,
  "explanation": "Translating every IntegrityError hides the real cause. Check sqlite_errorname (or validate the input first) and re-raise everything else." }
```

## 5. Your turn

Build `UserRepository` for the messenger's users table: getters, `add`, `rename` and keyset `page`. The tests are given; run them after each method. This is the shape PRJ-02 will ask you to build for messages, so take the time to make each method's error path right, not just the happy path.

```exercise
DB.M04.L03.E1
```
