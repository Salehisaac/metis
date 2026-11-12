---
{
  "id": "DB.M04.L01",
  "title": "Placeholders, and why escaping isn't enough",
  "difficulty": "intermediate",
  "minutes": 65,
  "prerequisites": ["DB.M03", "PY.M05"],
  "objectives": [
    "Demonstrate SQL injection on a toy database: bypassing a WHERE and reading another table with UNION",
    "Explain, with two concrete counterexamples, why escaping quotes by hand is not a defence",
    "Use qmark (?) and named (:name) placeholders correctly, including the parameter-sequence rules and the 3.12 DeprecationWarning",
    "Handle the parts of SQL that can't be placeholders (column names, ASC/DESC) with an allow-list, and build an IN list of any length safely"
  ],
  "why": "In the assessment you saw the injection risk but proposed escaping quotes yourself. That fix works in one context and fails in others, and it fails silently. Placeholders don't depend on context at all, which is why OWASP lists them first and calls manual escaping strongly discouraged. Every query you write from now on, including PRJ-02, uses them.",
  "applications": [
    "Every query that includes user input: search boxes, ids from URLs, filters from API parameters",
    "Sortable admin tables (allow-listed ORDER BY)",
    "Batch lookups by a list of ids"
  ],
  "exercises": ["DB.M04.L01.E1"],
  "sources": [
    {
      "title": "OWASP SQL Injection Prevention Cheat Sheet",
      "url": "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
      "version": "OWASP Cheat Sheet Series (current web version)",
      "verified": "2026-11-12",
      "claims": ["Preferred defence: parameterized queries for dynamic data", "Structural parts that can't be parameterized (table names, column names, sort direction) must be mapped to a strict allow-list of fixed values", "Parameter markers represent data values, not table names, column names or keywords like ASC and DESC", "Manual escaping is strongly discouraged and error-prone", "Least privilege for database accounts"]
    },
    {
      "title": "sqlite3: DB-API 2.0 interface for SQLite databases",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Always use placeholders instead of string formatting to bind values, to avoid SQL injection", "qmark style: parameters must be a sequence whose length matches the number of placeholders, else ProgrammingError", "named style: parameters must be a dict with keys for all named parameters; extra items are ignored", "3.12: DeprecationWarning if named placeholders get a sequence; ProgrammingError from 3.14", "Numeric placeholders (?NNN as in PEP 249 numeric style) are not supported"]
    },
    {
      "title": "MySQL 8.4 Reference Manual: String Literals",
      "url": "https://dev.mysql.com/doc/refman/8.4/en/string-literals.html",
      "version": "MySQL 8.4 Reference Manual (not run here: no MySQL server on this machine)",
      "verified": "2026-11-12",
      "claims": ["Inside a string, backslash starts an escape sequence unless NO_BACKSLASH_ESCAPES is enabled", "\\' is an escaped single quote; '' inside a '-quoted string is also a quote"]
    }
  ]
}
---
## 1. The attack, on a toy database

A small database with a table nobody should be able to read through the search box:

```python
import sqlite3

conn = sqlite3.connect(":memory:")
conn.executescript("""
CREATE TABLE members (id INTEGER PRIMARY KEY, name TEXT NOT NULL, plan TEXT NOT NULL);
CREATE TABLE api_keys (member_id INTEGER, secret TEXT);
INSERT INTO members VALUES (1, 'kim', 'free'), (2, 'lee', 'pro'), (3, 'o''neil', 'free');
INSERT INTO api_keys VALUES (1, 'sk-kim-123'), (2, 'sk-lee-456');
""")


def find_unsafe(name):
    return conn.execute(f"SELECT id, name FROM members WHERE name = '{name}'").fetchall()


print(find_unsafe("kim"))
print(find_unsafe("x' OR '1'='1"))
print(find_unsafe("x' UNION SELECT member_id, secret FROM api_keys --"))
try:
    find_unsafe("x'; DROP TABLE members; --")
except sqlite3.ProgrammingError as e:
    print("ProgrammingError:", e)
try:
    print(find_unsafe("o'neil"))
except sqlite3.OperationalError as e:
    print("OperationalError:", e)
```

```text
[(1, 'kim')]
[(1, 'kim'), (2, 'lee'), (3, "o'neil")]
[(1, 'sk-kim-123'), (2, 'sk-lee-456')]
ProgrammingError: You can only execute one statement at a time.
OperationalError: near "neil": syntax error
```

The f-string pastes the input into the SQL text, so the input **becomes SQL**:

- `x' OR '1'='1` closes the string and adds a condition that's always true: every member comes back.
- The UNION payload appends a second query, and `--` comments out the leftover quote: **the API keys come back as search results**.
- `execute()` refused the stacked `DROP TABLE` because it runs one statement at a time. That's luck, not a defence: the UNION attack needed only one statement.
- And an honest user called o'neil crashes it.

In Go, this is `db.Query(fmt.Sprintf("... WHERE name = '%s'", name))`: same bug, same attacks.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE notes(id INTEGER PRIMARY KEY, owner TEXT, body TEXT);\nINSERT INTO notes(owner, body) VALUES ('ana', 'a1'), ('ben', 'b1'), ('ben', 'b2');''')\nowner = \"nobody' OR owner = 'ben\"\nprint(len(c.execute(f\"SELECT body FROM notes WHERE owner = '{owner}'\").fetchall()))",
  "answer": "2",
  "explanation": "The SQL becomes `WHERE owner = 'nobody' OR owner = 'ben'`: the input added its own condition and reads ben's two notes." }
```

## 2. Your fix: escape the quotes

Your assessment answer was to escape quotes. In SQL, a quote inside a string literal is written as two quotes, so:

```python
def quote(value):
    return value.replace("'", "''")


def find_escaped(name):
    return conn.execute(f"SELECT id, name FROM members WHERE name = '{quote(name)}'").fetchall()


def member_by_id(member_id):
    return conn.execute(f"SELECT id, name FROM members WHERE id = {quote(member_id)}").fetchall()


print(find_escaped("o'neil"))
print(find_escaped("x' OR '1'='1"))
print(member_by_id("2"))
print(member_by_id("0 OR 1=1"))
print(member_by_id("0 UNION SELECT member_id, secret FROM api_keys"))
```

```text
[(3, "o'neil")]
[]
[(2, 'lee')]
[(1, 'kim'), (2, 'lee'), (3, "o'neil")]
[(1, 'sk-kim-123'), (2, 'sk-lee-456')]
```

Inside a quoted string, in SQLite, it holds: o'neil works and the OR payload finds nothing. But the moment the value isn't inside quotes, **there's nothing to escape**. `id = 0 OR 1=1` and the UNION payload contain no quotes at all, pass through `quote()` unchanged, and leak the keys again. ids come from URLs as strings all the time.

It fails in other ways too:

- **The rules depend on the database and its settings.** In MySQL, a backslash inside a string starts an escape sequence (unless the `NO_BACKSLASH_ESCAPES` mode is on), so `\'` is an escaped quote. Input `\' OR 1=1 -- ` becomes `\'' OR 1=1 -- ` after doubling: MySQL reads `\'` as a literal quote, the next `'` closes the string, and the attack runs. *Not run on this machine (no MySQL server); behaviour per the cited MySQL docs.*
- **It must never be forgotten.** One call site without `quote()`, in a codebase with hundreds of queries, is enough.
- **It can't help with column names or ORDER BY,** where there are no quotes either (section 4).

OWASP's cheat sheet puts it bluntly: manual escaping is *strongly discouraged* and error-prone; use parameterized queries.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "The value is escaped by doubling quotes. What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE orders(id INTEGER PRIMARY KEY, owner TEXT);\nINSERT INTO orders(owner) VALUES ('ana'), ('ben'), ('cy');''')\nraw_id = '1 OR 1=1'\nsafe = raw_id.replace(\"'\", \"''\")\nprint(len(c.execute(f'SELECT owner FROM orders WHERE id = {safe}').fetchall()))",
  "answer": "3",
  "explanation": "The payload contains no quotes, so escaping changes nothing, and `id = 1 OR 1=1` returns every order." }
```

## 3. Placeholders: the value never becomes SQL

With a placeholder, the SQL text is fixed and the value is sent **separately**, bound to the slot after the statement has been parsed. It can't change the statement's structure, whatever it contains:

```python
print(conn.execute("SELECT id, name FROM members WHERE name = ?", ("o'neil",)).fetchall())
print(conn.execute("SELECT id, name FROM members WHERE name = ?", ("x' OR '1'='1",)).fetchall())
print(conn.execute("SELECT id, name FROM members WHERE id = ?", ("0 OR 1=1",)).fetchall())
print(conn.execute("SELECT id, name FROM members WHERE plan = :plan AND id > :min_id", {"plan": "free", "min_id": 0}).fetchall())
```

```text
[(3, "o'neil")]
[]
[]
[(1, 'kim'), (3, "o'neil")]
```

No escaping, no context to get right: quotes, numbers and UNION payloads are all just values that match nothing. Two styles:

- **qmark** `?`: parameters are a **sequence** (usually a tuple) with exactly one item per `?`.
- **named** `:name`: parameters are a **dict** with every name; extra keys are ignored.

Two mistakes the module catches for you:

```python
try:
    conn.execute("SELECT id FROM members WHERE name = ?", "kim")
except sqlite3.ProgrammingError as e:
    print("ProgrammingError:", e)
with warnings.catch_warnings(record=True) as caught:   # import warnings
    warnings.simplefilter("always")
    conn.execute("SELECT id FROM members WHERE name = :name", ("kim",))
    print(caught[0].category.__name__)
```

```text
ProgrammingError: Incorrect number of bindings supplied. The current statement uses 1, and there are 3 supplied.
DeprecationWarning
```

- A bare string is a sequence of characters, so `"kim"` counts as 3 parameters. Write `("kim",)` with the comma.
- Named placeholders with a tuple work in 3.12 but warn; the docs say it becomes a `ProgrammingError` in 3.14. Use a dict.

In Go, `db.Query("... WHERE name = ?", name)` is the same mechanism, so you already use it daily; the bug only appears when someone reaches for `fmt.Sprintf`.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE notes(id INTEGER PRIMARY KEY, owner TEXT, body TEXT);\nINSERT INTO notes(owner, body) VALUES ('ana', 'a1'), ('ben', 'b1'), (\"o'hara\", 'o1');''')\nfor owner in [\"nobody' OR owner = 'ben\", \"o'hara\"]:\n    print(c.execute('SELECT body FROM notes WHERE owner = ?', (owner,)).fetchall())",
  "answer": "[]\n[('o1',)]",
  "explanation": "With a placeholder the payload is just an owner name nobody has, and o'hara needs no escaping." }
```

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "Which call is correct for `SELECT * FROM users WHERE id = ?` with user_id = 7?",
  "options": ["conn.execute(sql, user_id)", "conn.execute(sql, (user_id))", "conn.execute(sql, (user_id,))", "conn.execute(sql % user_id)"], "answer": 2,
  "explanation": "Parameters must be a sequence. (user_id) is just 7 in parentheses, not a tuple; (user_id,) is a one-element tuple. The last one is string formatting again." }
```

## 4. What a placeholder can't be

Placeholders stand for **values only**: not table names, not column names, not keywords like ASC and DESC. `ORDER BY ?` is legal but sorts by a constant (the string you passed), and `SELECT id FROM ?` is a syntax error. For those parts, OWASP's rule is an **allow-list**: the user's input only *chooses* among SQL fragments you wrote yourself.

```python
ORDER_CHOICES = {
    "name": "name",
    "newest": "id DESC",
    "plan": "plan, name",
}


def members_sorted(order):
    try:
        order_sql = ORDER_CHOICES[order]
    except KeyError:
        raise ValueError(f"can't sort by {order!r}") from None
    return conn.execute(f"SELECT name FROM members ORDER BY {order_sql}").fetchall()


print(members_sorted("newest"))
print(members_sorted("plan"))
try:
    members_sorted("name; DROP TABLE members")
except ValueError as e:
    print("ValueError:", e)
```

```text
[("o'neil",), ('lee',), ('kim',)]
[('kim',), ("o'neil",), ('lee',)]
ValueError: can't sort by 'name; DROP TABLE members'
```

The f-string here is safe because `order_sql` can only ever be one of three strings in your source code. Never do it the other way round, checking that the input "looks safe" and then pasting the input itself.

**IN lists** have a variable number of values. Generate one `?` per value, and pass the values as parameters:

```python
names = ["kim", "o'neil", "nobody"]
placeholders = ",".join(["?"] * len(names))
print(placeholders)
print(conn.execute(f"SELECT id, name FROM members WHERE name IN ({placeholders}) ORDER BY id", names).fetchall())
```

```text
?,?,?
[(1, 'kim'), (3, "o'neil")]
```

Again the f-string inserts only question marks. Watch the empty list: `IN ()` is not something to rely on across databases, so return early when there are no values.

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "`conn.execute(\"SELECT * FROM messages ORDER BY ? DESC\", (column,))` sorts the messages by the column the user picked.", "answer": false,
  "explanation": "The placeholder is a value, so this sorts by a constant string, which leaves the order undefined. Column names need an allow-list that maps the user's choice to fixed SQL text." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "In a code review you find `cur.execute(\"SELECT * FROM users WHERE email = '%s'\" % email.replace(\"'\", \"''\"))` with the comment 'escaped, so safe'. What do you write in the review?",
  "model": "Use a placeholder: cur.execute(\"SELECT * FROM users WHERE email = ?\", (email,)). Manual escaping depends on context and dialect: it does nothing for values outside quotes (numbers), the rules differ between databases (MySQL treats backslash as an escape character by default), and one forgotten call is enough. With placeholders the value is never parsed as SQL, and OWASP strongly discourages manual escaping.",
  "explanation": "Placeholders are context-free; escaping isn't." }
```

## 5. Your turn

Four functions from an admin tool build SQL with f-strings. Two of them also crash on perfectly harmless input. Rewrite them; the tests include real injection payloads.

```exercise
DB.M04.L01.E1
```
