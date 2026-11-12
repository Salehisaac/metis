---
{
  "id": "DB.M02.L01",
  "title": "Keys and relationships: designing the messaging schema",
  "difficulty": "intermediate",
  "minutes": 70,
  "prerequisites": ["DB.M01"],
  "objectives": [
    "Model one-to-many relationships with a foreign key and many-to-many relationships with a junction table",
    "Choose a primary key, including a composite natural key, that enforces an 'only once' rule",
    "Turn on foreign key enforcement in SQLite and predict what ON DELETE CASCADE and the default NO ACTION do",
    "Spot the redundancy problems in a denormalized design (copied names, comma-separated lists) and normalize it",
    "Read and justify each table of the academy's messaging schema"
  ],
  "why": "Every JOIN in the next three lessons follows a foreign key, so you need to know where they come from. A good schema makes invalid data impossible; a weak one leaves every rule to application code, where a single forgotten check corrupts data. Your day job's schema was designed by someone else; this lesson is about being able to design one yourself.",
  "applications": [
    "Users, chats, memberships and messages: the core of any messenger",
    "Tags on posts, roles of users, products in orders: all many-to-many",
    "Deciding what happens to child rows when a parent row is deleted"
  ],
  "exercises": ["DB.M02.L01.E1"],
  "sources": [
    {
      "title": "SQLite Foreign Key Support",
      "url": "https://www.sqlite.org/foreignkeys.html",
      "version": "SQLite docs (current); behaviour checked locally on SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["Foreign key constraints are disabled by default and must be enabled per connection with PRAGMA foreign_keys = ON", "Changing foreign_keys inside a multi-statement transaction has no effect and no error", "The default action is NO ACTION; CASCADE deletes the child rows; SET NULL sets the child key to NULL; RESTRICT prohibits the delete", "The parent key must be the primary key or have a UNIQUE constraint", "An index on the child key columns is recommended"]
    },
    {
      "title": "SQLite: CREATE TABLE",
      "url": "https://www.sqlite.org/lang_createtable.html",
      "version": "SQLite docs (current); behaviour checked locally on SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["Composite primary keys are supported; each row needs a unique combination of the key columns", "CHECK is evaluated on insert and update; a CHECK that evaluates to NULL is not a violation", "Table constraints such as PRIMARY KEY (a, b) and CHECK follow the column definitions"]
    },
    {
      "title": "MySQL 8.4 Reference Manual: FOREIGN KEY Constraints",
      "url": "https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html",
      "version": "MySQL 8.4 Reference Manual (not run here: no MySQL server on this machine)",
      "verified": "2026-11-12",
      "claims": ["InnoDB checks foreign key constraints; checking is controlled by foreign_key_checks, which is enabled by default"]
    }
  ]
}
---
## 1. One-to-many: the foreign key

A blog: each post has exactly one author, and an author has many posts. That's **one-to-many**, and you model it by storing the "one" side's key on the "many" side:

```python
import sqlite3

SCHEMA = """
CREATE TABLE authors (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE posts (
    id        INTEGER PRIMARY KEY,
    author_id INTEGER NOT NULL REFERENCES authors(id),
    title     TEXT NOT NULL
);
CREATE TABLE tags (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE post_tags (
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    tag_id  INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, tag_id)
);
"""
```

`author_id ... REFERENCES authors(id)` is a **foreign key**: every `posts.author_id` must match an existing `authors.id`. In Go terms, it's like a `Post` struct holding an `AuthorID` rather than a copy of the `Author`. The referenced column must be a primary key or UNIQUE.

**SQLite's big surprise:** foreign keys are **off by default**, for backwards compatibility, and must be turned on **for each connection**:

```python
conn = sqlite3.connect(":memory:")
conn.executescript(SCHEMA)
print(conn.execute("PRAGMA foreign_keys").fetchone())
conn.execute("INSERT INTO posts (author_id, title) VALUES (?, ?)", (42, "orphan"))
print("orphan accepted:", conn.execute("SELECT id, author_id FROM posts").fetchall())

conn = sqlite3.connect(":memory:")
conn.execute("PRAGMA foreign_keys = ON")
conn.executescript(SCHEMA)
print(conn.execute("PRAGMA foreign_keys").fetchone())
try:
    conn.execute("INSERT INTO posts (author_id, title) VALUES (?, ?)", (42, "orphan"))
except sqlite3.IntegrityError as e:
    print("IntegrityError:", e)
```

```text
(0,)
orphan accepted: [(1, 42)]
(1,)
IntegrityError: FOREIGN KEY constraint failed
```

Without the PRAGMA, the REFERENCES clause is decoration. In MySQL, InnoDB checks foreign keys by default (the `foreign_key_checks` variable is on), so this step is easy to forget when you come from MySQL. The PRAGMA also has **no effect inside an open transaction** (and gives no error), so run it right after connecting. From now on, every DB exercise's `make_db()` does this.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE teams(id INTEGER PRIMARY KEY);\nCREATE TABLE players(id INTEGER PRIMARY KEY, team_id INTEGER NOT NULL REFERENCES teams(id));''')\nc.execute('INSERT INTO players (team_id) VALUES (7)')\nprint(c.execute('SELECT count(*) FROM players').fetchone()[0])",
  "answer": "1",
  "explanation": "No PRAGMA foreign_keys = ON on this connection, so SQLite doesn't check the reference and the orphan row is inserted." }
```

## 2. Many-to-many: the junction table

A post has many tags and a tag is on many posts. Neither side can hold "the" other's key, so the relationship gets **its own table**, `post_tags`, with one row per (post, tag) pair. Its primary key is the pair itself: a **composite key**. That one line also enforces "a tag is on a post at most once":

```python
conn.executescript("""
INSERT INTO authors (id, name) VALUES (1, 'kim'), (2, 'lee');
INSERT INTO posts (id, author_id, title) VALUES (10, 1, 'Go to Python'), (11, 1, 'SQLite tips'), (12, 2, 'Hello');
INSERT INTO tags (id, name) VALUES (1, 'python'), (2, 'sql'), (3, 'go');
INSERT INTO post_tags (post_id, tag_id) VALUES (10, 1), (10, 3), (11, 2), (11, 1);
""")
try:
    conn.execute("INSERT INTO post_tags (post_id, tag_id) VALUES (10, 1)")
except sqlite3.IntegrityError as e:
    print("IntegrityError:", e)
```

```text
IntegrityError: UNIQUE constraint failed: post_tags.post_id, post_tags.tag_id
```

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "A user can have many roles (admin, moderator, ...) and a role belongs to many users. How do you model it?",
  "options": ["A roles TEXT column on users, like 'admin,moderator'", "A role_id column on users", "A user_roles table with user_id and role_id, primary key (user_id, role_id)", "A user_id column on roles"], "answer": 2,
  "explanation": "Many-to-many needs a junction table. A role_id on users allows only one role per user; a user_id on roles allows only one user per role." }
```

## 3. What happens on delete

When you delete a parent row that still has children, the foreign key's `ON DELETE` action decides:

- **NO ACTION** (the default) and **RESTRICT**: the delete fails. Your children are protected.
- **CASCADE**: the children are deleted too.
- **SET NULL**: the children stay, with the key set to NULL (the column must allow NULL).

```python
try:
    conn.execute("DELETE FROM authors WHERE id = 1")
except sqlite3.IntegrityError as e:
    print("IntegrityError:", e)
conn.execute("DELETE FROM posts WHERE id = 10")
print(conn.execute("SELECT post_id, tag_id FROM post_tags ORDER BY post_id, tag_id").fetchall())
conn.execute("DELETE FROM tags WHERE id = 1")
print(conn.execute("SELECT post_id, tag_id FROM post_tags ORDER BY post_id, tag_id").fetchall())
```

```text
IntegrityError: FOREIGN KEY constraint failed
[(11, 1), (11, 2)]
[(11, 2)]
```

kim still has posts, so deleting kim fails (NO ACTION). Deleting post 10 removed its two `post_tags` rows (CASCADE), and deleting the tag 'python' removed its last link.

**Choose per relationship.** CASCADE suits rows that mean nothing without their parent (a post's tags, a chat's messages). For "deleting a user", erasing their messages from everyone else's chats is a product decision, so the default, which refuses, is the safer choice.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute('PRAGMA foreign_keys = ON')\nc.executescript('''CREATE TABLE chats(id INTEGER PRIMARY KEY);\nCREATE TABLE msgs(id INTEGER PRIMARY KEY, chat_id INTEGER REFERENCES chats(id) ON DELETE CASCADE);\nCREATE TABLE pins(msg_id INTEGER REFERENCES msgs(id) ON DELETE SET NULL);\nINSERT INTO chats VALUES (1), (2);\nINSERT INTO msgs VALUES (10, 1), (11, 1), (12, 2);\nINSERT INTO pins VALUES (10), (12);''')\nc.execute('DELETE FROM chats WHERE id = 1')\nprint(c.execute('SELECT id FROM msgs').fetchall(), c.execute('SELECT msg_id FROM pins ORDER BY msg_id').fetchall())",
  "answer": "[(12,)] [(None,), (12,)]",
  "explanation": "Deleting chat 1 cascades to messages 10 and 11. Deleting message 10 then triggers SET NULL on the pin that pointed to it. Actions chain." }
```

## 4. Normalization: store each fact once

Two designs that look convenient and cause trouble later:

| Design | Problem |
|---|---|
| `posts(author_name TEXT, ...)` instead of `author_id` | kim renames to "Kim Park": you must update every post, and one missed row means two spellings of the same person. Nothing stops a post for an author who doesn't exist. |
| `posts(tags TEXT)` holding `'python,sql'` | No foreign key, so typos ('pyhton') get in. "Posts tagged go" becomes `tags LIKE '%go%'`, which also matches 'golang' and 'mongo'. Removing a tag means string surgery on every row. |

The fix in both cases is the same: **one fact in one place**, and other tables refer to it by key. That's the core of normalization. You'll sometimes *denormalize* on purpose (a cached `message_count` on chats, say) for speed, but then it's a decision with a plan to keep the copy correct, not an accident.

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "Storing a chat's member ids as a comma-separated string, like '1,2,5', lets the database reject a member id that doesn't exist.", "answer": false,
  "explanation": "A foreign key works on a column value, not on pieces of a string. Use a junction table, chat_members, with a foreign key per column." }
```

## 5. The academy's messaging schema, table by table

Open `chatdb.py` in any DB exercise and compare it with this summary:

- **users**(id, username UNIQUE, created_at). Usernames are unique, but everything refers to `id`, so renaming a user touches one row.
- **chats**(id, kind CHECK in ('direct', 'group'), title, created_at). `title` may be NULL: direct chats don't have one.
- **chat_members**(chat_id → chats ON DELETE CASCADE, user_id → users, joined_at), **PRIMARY KEY (chat_id, user_id)**. The junction table for the many-to-many between users and chats. It also has a column of its own, `joined_at`: a fact about the *relationship*, which belongs nowhere else.
- **messages**(id, chat_id → chats ON DELETE CASCADE, sender_id → users, body NOT NULL, sent_at, edited_at). One chat has many messages; one user sends many messages. Deleting a chat deletes its messages; deleting a user who sent messages fails.

What the schema does **not** enforce: that a message's sender is a member of its chat. That rule spans two relationships, and a plain foreign key can't express it. The application checks it, inside a transaction (DB.M03).

Foreign keys like `messages.chat_id` should normally get an index, because "messages of chat X" and the cascade on delete both search by that column. Indexes are DB.M05; the sample data is too small to need them.

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "Where does 'the time user 3 joined chat 1' belong in this schema?",
  "options": ["users.created_at", "chats.created_at", "chat_members.joined_at", "A new column on messages"], "answer": 2,
  "explanation": "It's a fact about one (chat, user) pair, so it lives on the junction row for that pair." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "Your colleague proposes adding `sender_username TEXT` to messages 'so the chat screen doesn't need a JOIN'. What do you answer?",
  "model": "It duplicates a fact that lives in users. When a user renames, every old message shows the old name unless you update them all, and nothing keeps the copies in sync. Keep sender_id and JOIN users (next lesson); the join on a primary key is cheap. Denormalize only with a measured need and a plan for keeping the copy correct.",
  "explanation": "One fact in one place; refer to it by key." }
```

## 6. Your turn

Design two new tables for the messenger, emoji reactions and blocking, so that **the database** rejects every invalid row. The tests never call your Python logic; they only insert and delete rows and check whether the database accepts them. Read the docstring in `schema_ext.py` carefully: each sentence is one constraint.

```exercise
DB.M02.L01.E1
```
