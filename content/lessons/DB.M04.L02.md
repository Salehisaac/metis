---
{
  "id": "DB.M04.L02",
  "title": "LIKE patterns, executemany and row factories",
  "difficulty": "intermediate",
  "minutes": 60,
  "prerequisites": ["DB.M04.L01"],
  "objectives": [
    "Explain why a placeholder doesn't stop % and _ in user input from acting as LIKE wildcards, and escape them with an ESCAPE clause",
    "Insert or update many rows with executemany, from a list or a generator, as one transaction, and read rowcount and lastrowid correctly",
    "Use sqlite3.Row for name-based access, and a custom row factory that returns dataclass objects",
    "Choose where to set a row factory (connection or cursor) and predict what other queries then return"
  ],
  "why": "Search boxes are where 'safe' code still misbehaves: a placeholder stops injection, but a user searching for '50%' or 'snake_case' gets the wrong results. Bulk imports and readable result rows are the other two tools you need before building a repository layer in the next lesson and a message store in PRJ-02.",
  "applications": [
    "Username and message search that treats the user's text literally",
    "Importing users or messages from a file in one transaction",
    "Returning domain objects (dataclasses) instead of anonymous tuples"
  ],
  "exercises": ["DB.M04.L02.E1"],
  "sources": [
    {
      "title": "SQLite: SQL Language Expressions (LIKE and ESCAPE)",
      "url": "https://www.sqlite.org/lang_expr.html",
      "version": "SQLite docs (current); behaviour checked locally on SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["In LIKE, % matches any sequence of zero or more characters and _ matches any single character", "LIKE is case-insensitive for ASCII characters only, by default", "With ESCAPE, the escape character followed by %, _ or itself matches a literal %, _ or escape character"]
    },
    {
      "title": "sqlite3: DB-API 2.0 interface for SQLite databases",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["executemany executes a parameterized DML statement for every item in parameters", "lastrowid is not updated by executemany()", "rowcount is updated by execute() and executemany()", "Row provides indexed and case-insensitive named access to columns, supports keys(), len, iteration and equality", "row_factory is None by default (tuples); it can be set on a connection or a cursor", "Cursor.description holds the column names of the last query"]
    }
  ]
}
---
## 1. LIKE: the placeholder is safe, the pattern isn't literal

A product search, done the way DB.M04.L01 taught, with a placeholder:

```python
import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
conn.executemany("INSERT INTO products (name) VALUES (?)",
                 [("50% off mug",), ("500 ml bottle",), ("snake_case poster",), ("snake-case mug",), ("C:\\tmp sign",)])

def search_naive(text):
    return conn.execute("SELECT name FROM products WHERE name LIKE ? ORDER BY id", (f"%{text}%",)).fetchall()

print(search_naive("50%"))
print(search_naive("snake_case"))
```

```text
[('50% off mug',), ('500 ml bottle',)]
[('snake_case poster',), ('snake-case mug',)]
```

No injection is possible here. But inside LIKE, the **value** is a pattern: `%` means "any sequence of characters" and `_` means "any single character". The user typed `50%` and got the 500 ml bottle; typed `snake_case` and got `snake-case`. For a search box that's a bug; for something like "delete messages matching what the user typed" it's dangerous.

The fix is an **ESCAPE clause**: declare an escape character, and put it before every `%`, `_` (and the escape character itself) in the user's text.

```python
def like_escape(text):
    for ch in ("\\", "%", "_"):  # the escape character itself first
        text = text.replace(ch, "\\" + ch)
    return text

def search(text):
    pattern = f"%{like_escape(text)}%"
    return conn.execute("SELECT name FROM products WHERE name LIKE ? ESCAPE '\\' ORDER BY id", (pattern,)).fetchall()

print(search("50%"))
print(search("snake_case"))
print(search("\\"))
print(search("MUG"))
print(like_escape("50%_\\x"))
```

```text
[('50% off mug',)]
[('snake_case poster',)]
[('C:\\tmp sign',)]
[('50% off mug',), ('snake-case mug',)]
50\%\_\\x
```

- `ESCAPE '\'` (written `'\\'` inside the Python string) makes `\%`, `\_` and `\\` match a literal `%`, `_` and `\`.
- **The escape character must be escaped first.** Otherwise the backslashes you add for `%` and `_` get doubled in the next step and stop escaping anything.
- The `%...%` around it are *your* wildcards, added after escaping.
- `MUG` found 'mug': LIKE ignores case, but only for ASCII letters ('Ä' and 'ä' don't match each other by default).

**Isn't this the escaping DB.M04.L01 said never to do?** No. That was escaping a value to splice it into the SQL **text**. This value still travels as a parameter; you're only telling LIKE which characters in it are literal. The statement stays fixed.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute('CREATE TABLE files(name TEXT)')\nc.executemany('INSERT INTO files VALUES (?)', [('a_1.txt',), ('ab1.txt',), ('a-1.txt',)])\nprint(c.execute('SELECT count(*) FROM files WHERE name LIKE ?', ('a_1%',)).fetchone()[0], c.execute(\"SELECT count(*) FROM files WHERE name LIKE ? ESCAPE '!'\", ('a!_1%',)).fetchone()[0])",
  "answer": "3 1",
  "explanation": "Unescaped, _ matches any one character, so all three names match. With ESCAPE '!', `!_` is a literal underscore: only a_1.txt." }
```

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "A helper escapes LIKE input with `text.replace('%', '\\\\%').replace('_', '\\\\_').replace('\\\\', '\\\\\\\\')` (backslash replaced last) and uses ESCAPE '\\'. What goes wrong for the input `50%`?",
  "options": ["Nothing", "It becomes `50\\\\%`: the backslash added for % is itself doubled, so the pair now means a literal backslash and % is a wildcard again", "It raises an error", "The placeholder escapes it a second time"], "answer": 1,
  "explanation": "Escape the escape character first, then % and _." }
```

## 2. executemany: one statement, many parameter sets

`executemany(sql, seq)` runs the same statement once per item of `seq`. Items are tuples for `?` or dicts for `:name`, and `seq` can be any iterable, including a generator that reads a file line by line.

```python
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, price INTEGER NOT NULL)")
rows = [("mug", 8), ("bottle", 12), ("poster", 15)]
with conn:
    cur = conn.executemany("INSERT INTO products (name, price) VALUES (?, ?)", rows)
print(cur.rowcount, cur.lastrowid)
more = [{"name": "pen", "price": 2}, {"name": "mug", "price": 9}]
try:
    with conn:
        conn.executemany("INSERT INTO products (name, price) VALUES (:name, :price)", more)
except sqlite3.IntegrityError as e:
    print("IntegrityError:", e)
print(conn.execute("SELECT name FROM products ORDER BY id").fetchall())
with conn:
    cur = conn.executemany("UPDATE products SET price = price + 1 WHERE name = ?", (("mug",), ("nope",), ("poster",)))
print(cur.rowcount)
```

```text
3 None
IntegrityError: UNIQUE constraint failed: products.name
[('mug',), ('bottle',), ('poster',)]
2
```

- `rowcount` is the **total** over all executions (3 inserted; later 2 updated, because 'nope' matched nothing).
- `lastrowid` is **not** updated by executemany (it's still `None` here). If you need each new id, use `execute()` per row, or SQLite's `RETURNING`.
- Inside `with conn:`, the whole batch is one transaction: the duplicate 'mug' rolled back 'pen' too. Without it, in the default mode, the batch would still be pending until a commit, and in `autocommit=True` mode the rows before the failure would stay.

In Go you'd prepare a statement and loop `stmt.Exec(...)` inside a `tx`; executemany is that loop, done by the driver.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute('CREATE TABLE tags(id INTEGER PRIMARY KEY, name TEXT UNIQUE)')\nwith c:\n    c.executemany('INSERT INTO tags(name) VALUES (?)', [('go',), ('py',)])\ntry:\n    with c:\n        c.executemany('INSERT INTO tags(name) VALUES (?)', (('sql',), ('db',), ('go',)))\nexcept sqlite3.IntegrityError:\n    pass\nprint(c.execute('SELECT name FROM tags ORDER BY id').fetchall())",
  "answer": "[('go',), ('py',)]",
  "explanation": "The second batch failed on the duplicate 'go'; the with block rolled back 'sql' and 'db' too." }
```

## 3. Row factories: names instead of positions

By default a row is a tuple, so code says `row[1]` and breaks silently when someone reorders the SELECT. Set a **row factory** to get something better:

```python
conn = sqlite3.connect(":memory:")
conn.executescript("""
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, price INTEGER NOT NULL);
INSERT INTO products (name, price) VALUES ('mug', 8), ('bottle', 12);
""")
row = conn.execute("SELECT id, name, price FROM products WHERE id = 1").fetchone()
print(row, row[1])

conn.row_factory = sqlite3.Row
row = conn.execute("SELECT id, name, price FROM products WHERE id = 1").fetchone()
print(type(row).__name__, row["name"], row["PRICE"], row[0], row.keys(), dict(row))
print(tuple(row) == (1, "mug", 8))
```

```text
(1, 'mug', 8) mug
Row mug 8 1 ['id', 'name', 'price'] {'id': 1, 'name': 'mug', 'price': 8}
True
```

`sqlite3.Row` allows access by index **or** by name (case-insensitive), has `keys()`, and converts to a dict. It's built into the module and cheap.

For a domain type, write your own factory: a function `(cursor, row) -> object`. `cursor.description` holds the column names of the query, like `rows.Columns()` in Go:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    price: int


def product_factory(cursor, row):
    names = [d[0] for d in cursor.description]
    return Product(**dict(zip(names, row)))


cursor = conn.cursor()
cursor.row_factory = product_factory
print(cursor.execute("SELECT id, name, price FROM products ORDER BY id").fetchall())
print(conn.execute("SELECT name FROM products WHERE id = 2").fetchone()["name"])
try:
    cursor.execute("SELECT id, name FROM products").fetchone()
except TypeError as e:
    print("TypeError:", e)
```

```text
[Product(id=1, name='mug', price=8), Product(id=2, name='bottle', price=12)]
bottle
TypeError: Product.__init__() missing 1 required positional argument: 'price'
```

- A factory set on a **cursor** affects only that cursor; the connection still returns `sqlite3.Row` (the `["name"]` line). A factory set on the **connection** applies to every cursor created from it afterwards, including the ones `conn.execute()` creates for you.
- Matching by column name means the SELECT's column order doesn't matter, but a missing column fails loudly, which is what you want.
- A dataclass is a *mapping* from rows to your types, the job sqlx's `StructScan` does in Go.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute(\"CREATE TABLE u(id INTEGER PRIMARY KEY, name TEXT)\")\nc.execute(\"INSERT INTO u(name) VALUES ('ana')\")\nc.row_factory = sqlite3.Row\nr = c.execute('SELECT name, id FROM u').fetchone()\nprint(r[0], r['ID'], r.keys())",
  "answer": "ana 1 ['name', 'id']",
  "explanation": "Index 0 is the first selected column (name). Name access is case-insensitive. keys() follows the SELECT order." }
```

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "After `cur = conn.cursor(); cur.row_factory = sqlite3.Row`, `conn.execute(...)` also returns Row objects.", "answer": false,
  "explanation": "The factory was set on one cursor only. conn.execute creates a new cursor, which uses the connection's row_factory (None: tuples)." }
```

## 4. Your turn

Two functions for the messenger's users: a username search where the user's `%`, `_` and backslash are literal and the result is a list of `User` dataclass objects, and a bulk import that's all or nothing. Remember that the backslash in SQL's `ESCAPE '\'` is written `'\\'` inside a Python string.

```exercise
DB.M04.L02.E1
```
