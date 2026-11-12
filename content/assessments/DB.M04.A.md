---
{ "id": "DB.M04.A", "module": "DB.M04", "title": "DB.M04 module assessment: safe SQL from Python", "minutes": 15 }
---
Answer without the lessons open, without running the code and without AI. Only your **first** answer counts. a1 and a6 re-ask the assessment question you answered with "escape the quotes". If you miss more than one, ask the mentor for practice before PRJ-02.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "The id comes from a URL and is escaped by doubling quotes. What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE msgs(id INTEGER PRIMARY KEY, owner TEXT, body TEXT);\nINSERT INTO msgs(owner, body) VALUES ('ana', 'hi'), ('ben', 'secret'), ('cy', 'yo');''')\nraw = '1 OR 1=1'\nsafe = raw.replace(\"'\", \"''\")\nprint(len(c.execute(f'SELECT body FROM msgs WHERE id = {safe}').fetchall()), len(c.execute('SELECT body FROM msgs WHERE id = ?', (raw,)).fetchall()))",
  "answer": "3 0",
  "explanation": "The payload has no quotes, so escaping does nothing and `id = 1 OR 1=1` returns every row. With a placeholder the whole string is one value that equals no id." }
```

```quiz
{ "id": "a2", "type": "choice",
  "prompt": "An API lets clients sort by `?sort=created_at` or `?sort=username`. Which implementation is safe?",
  "options": ["conn.execute('SELECT * FROM users ORDER BY ?', (sort,))", "conn.execute(f'SELECT * FROM users ORDER BY {sort}')", "Look sort up in a dict of allowed values that map to fixed ORDER BY text; raise ValueError if it's missing; put the dict's value in the SQL", "Escape quotes in sort, then use an f-string"], "answer": 2,
  "explanation": "A placeholder can't be a column name (it would sort by a constant), and pasting input is injection. Only an allow-list of fixed SQL fragments is safe." }
```

```quiz
{ "id": "a3", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute('CREATE TABLE p(name TEXT)')\nc.executemany('INSERT INTO p VALUES (?)', [('100%',), ('1000',), ('10_0',)])\nprint(c.execute('SELECT count(*) FROM p WHERE name LIKE ?', ('%0%%',)).fetchone()[0], c.execute(\"SELECT count(*) FROM p WHERE name LIKE ? ESCAPE '\\\\'\", ('%0\\\\%%',)).fetchone()[0])",
  "answer": "3 1",
  "explanation": "Unescaped, the middle % is a wildcard, so every name with a 0 matches. Escaped as `\\%`, it must be a literal percent sign: only '100%'." }
```

```quiz
{ "id": "a4", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute('CREATE TABLE u(id INTEGER PRIMARY KEY, name TEXT UNIQUE)')\ntry:\n    with c:\n        c.executemany('INSERT INTO u(name) VALUES (?)', [('ana',), ('ben',), ('ana',)])\nexcept sqlite3.IntegrityError as e:\n    print(e.sqlite_errorname)\nprint(c.execute('SELECT count(*) FROM u').fetchone()[0])",
  "answer": "SQLITE_CONSTRAINT_UNIQUE\n0",
  "explanation": "The third row is a duplicate; the with block rolls back the whole batch, so no rows remain." }
```

```quiz
{ "id": "a5", "type": "truefalse",
  "prompt": "`conn.execute('SELECT * FROM users WHERE username = ?', username)` is correct when username is the string 'ana'.", "answer": false,
  "explanation": "Parameters must be a sequence of values; a string is a sequence of characters, so 'ana' counts as 3 parameters and raises ProgrammingError. Use (username,)." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "Explain to a teammate, in three or four sentences, why `name.replace(\"'\", \"''\")` before an f-string isn't a fix for SQL injection, and what to do instead (including for a sortable column).",
  "model": "Escaping only protects values inside quoted string literals, in one dialect: numbers and other unquoted positions need no quote to inject (`1 OR 1=1`), MySQL also treats backslash as an escape character by default, and one forgotten call is enough. Placeholders send the value separately from the SQL text, so it's never parsed as SQL, in any position and any dialect. Column names and ASC/DESC can't be placeholders, so map the user's choice through an allow-list of fixed SQL fragments. OWASP lists parameterized queries and allow-lists as the defences and strongly discourages manual escaping.",
  "explanation": "Placeholders for values, allow-lists for structure." }
```
