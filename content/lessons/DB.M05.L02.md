---
{
  "id": "DB.M05.L02",
  "title": "Composite and covering indexes: column order matters",
  "difficulty": "intermediate",
  "minutes": 80,
  "prerequisites": ["DB.M05.L01"],
  "objectives": [
    "Predict which WHERE terms a multi-column index can use: equality on the leading columns, then at most one range",
    "Order index columns so ORDER BY needs no USE TEMP B-TREE step",
    "Turn an index into a covering index and recognise USING COVERING INDEX in a plan",
    "Spot redundant indexes (one is a prefix of another) and remove them"
  ],
  "why": "Most real queries filter on one column and sort by another: a chat's messages by time, a user's orders by date. Getting the column order of one composite index right usually matters more than adding three more indexes, and it's the part AI-written migrations most often get backwards.",
  "applications": [
    "Paginated feeds and chat history (filter, then sort, then LIMIT)",
    "Count and existence queries that never need to open the table",
    "Reviewing a migration that adds an index: is the column order right, and is an old index now redundant?"
  ],
  "exercises": ["DB.M05.L02.E1"],
  "sources": [
    {
      "title": "The SQLite Query Optimizer: Query Planning",
      "url": "https://www.sqlite.org/queryplanner.html",
      "version": "SQLite docs, page updated 2026-03-22; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["In a multi-column index the left-most column orders the rows and later columns break ties", "A covering index contains every column the query uses, so the original table is never consulted", "An index on the ORDER BY column can make the sort a no-op", "Never keep two indexes where one is a prefix of the other; drop the shorter one"]
    },
    {
      "title": "The SQLite Query Optimizer Overview",
      "url": "https://www.sqlite.org/optoverview.html",
      "version": "SQLite docs, page updated 2025-05-31; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["The initial index columns must be used with =, IN or IS; the right-most used column may use inequalities", "There can be no gaps in the used columns", "Columns to the right of an inequality-only column are not normally used"]
    },
    {
      "title": "EXPLAIN QUERY PLAN",
      "url": "https://www.sqlite.org/eqp.html",
      "version": "SQLite docs, page updated 2025-05-31; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["SEARCH t USING COVERING INDEX i means the covering-index optimisation applies", "SCAN also covers iterating all rows in an index's order"]
    }
  ]
}
---
## 1. A composite index is a phone book

A phone book is sorted by **surname, then first name**. Finding "Karimi, Sara" is fast. Finding every "Karimi" is fast too: they're all next to each other. Finding every "Sara" means reading the whole book.

A composite index `ON messages (sender_id, created_at)` is the same: sorted by `sender_id`, and within one sender by `created_at`. In Go terms it's a slice sorted with `slices.SortFunc` comparing `sender_id` first and `created_at` to break ties. From that you get the rule the SQLite docs spell out:

- The **leading** columns must be compared with `=` (or `IN`, `IS`).
- The **last** column SQLite uses may be a range (`<`, `>`, `BETWEEN`).
- No gaps: if you don't constrain column 2, column 3 can't be searched.
- A column **after a range** isn't searched either: once you take "all senders from 5 to 9", their `created_at` values are no longer in one sorted run.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "There's an index `ON orders (customer_id, status, created_at)`. Which WHERE clause can use **all three** columns for searching?",
  "options": ["customer_id = ? AND status = ? AND created_at > ?", "customer_id = ? AND created_at > ?", "status = ? AND created_at > ?", "customer_id > ? AND status = ? AND created_at = ?"], "answer": 0,
  "explanation": "Equality on the first two, then a range on the last. Option 2 skips status (a gap), option 3 skips the first column, and in option 4 the range on customer_id stops the later columns from being searched." }
```

## 2. Filter, then sort: the column order decides

A user's profile page shows their latest 20 messages. Same query, three different indexes (each in a fresh database with only that index):

```python
FEED = "SELECT id, body FROM messages WHERE sender_id = ? ORDER BY created_at DESC LIMIT 20"
```

```console
# A: index on sender_id only
    SEARCH messages USING INDEX idx_messages_sender (sender_id=?)
    USE TEMP B-TREE FOR ORDER BY
# B: index on (sender_id, created_at)
    SEARCH messages USING INDEX idx_messages_sender_created (sender_id=?)
# C: index on (created_at, sender_id)
    SCAN messages USING INDEX idx_messages_created_sender
```

- **A** finds the sender's rows, but they come out in rowid order, so SQLite **sorts all of them** before it can take 20. A user with 100,000 messages pays for sorting 100,000 rows to show 20.
- **B** finds the sender's rows **already in `created_at` order**. SQLite walks them backwards for `DESC` and stops after 20. No sort step at all: the `ORDER BY` became free.
- **C** is the wrong way round. It **SCANs** the whole index in time order and checks each entry's sender. For a very active user it may find 20 quickly; for a quiet one it reads nearly everything.

**Rule of thumb:** equality columns first, then the column you sort or range on.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.execute('CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER, created_at TEXT)')\nconn.execute('CREATE INDEX idx_orders_customer ON orders (customer_id)')\nsql = 'SELECT id, total FROM orders WHERE customer_id = ? ORDER BY created_at DESC'\nfor *_, detail in conn.execute('EXPLAIN QUERY PLAN ' + sql, (5,)):\n    print(detail)",
  "answer": "SEARCH orders USING INDEX idx_orders_customer (customer_id=?)\nUSE TEMP B-TREE FOR ORDER BY",
  "explanation": "The index finds customer 5's orders but not in created_at order, so a separate sort step follows. An index on (customer_id, created_at) would remove it." }
```

## 3. Equality then range, and what a range blocks

With `(sender_id, created_at)` and with the reversed `(created_at, sender_id)`:

```console
-- index (sender_id, created_at)
SELECT id FROM messages WHERE sender_id = ? AND created_at >= ?
    SEARCH messages USING COVERING INDEX idx_messages_sender_created (sender_id=? AND created_at>?)
SELECT id FROM messages WHERE created_at >= ?
    SCAN messages USING COVERING INDEX idx_messages_sender_created
-- index (created_at, sender_id)
SELECT id FROM messages WHERE sender_id = ? AND created_at >= ?
    SEARCH messages USING COVERING INDEX idx_messages_created_sender (created_at>?)
```

- With the good order, the brackets show **both** columns: jump to sender 7, then to the first date, then read forward.
- Without a `sender_id` filter, the leading column isn't constrained, so it's a **SCAN** of the index (the "every Sara in the phone book" case).
- With the reversed order, only `created_at>?` is searched. Every message since that date, from every sender, is read and filtered. On a busy messenger that's most of the recent table.

The bracket text is abbreviated (`created_at>?` for `>=`). Read it as "which columns, with which kind of comparison".

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "With an index `ON messages (created_at, sender_id)`, the query `WHERE created_at > ? AND sender_id = ?` searches on both columns, because both appear in the WHERE clause.", "answer": false,
  "explanation": "Column order in the WHERE clause doesn't matter; index column order does. created_at is a range, so sender_id, which comes after it in the index, isn't searched." }
```

## 4. Covering indexes: never open the table

Look again at the plans above: `USING COVERING INDEX`. An index entry holds its columns **plus the rowid**, and `id INTEGER PRIMARY KEY` *is* the rowid. So `SELECT id ...` can be answered from the index alone. Ask for a column that isn't in the index and SQLite must do a second lookup in the table for every match:

```console
SELECT count(*) FROM messages WHERE sender_id = ? AND created_at >= ?
    SEARCH messages USING COVERING INDEX idx_messages_sender_created (sender_id=? AND created_at>?)
SELECT body FROM messages WHERE sender_id = ? AND created_at >= ?
    SEARCH messages USING INDEX idx_messages_sender_created (sender_id=? AND created_at>?)
-- after CREATE INDEX idx_messages_sender_created_body ON messages (sender_id, created_at, body)
SELECT body FROM messages WHERE sender_id = ? AND created_at >= ?
    SEARCH messages USING COVERING INDEX idx_messages_sender_created_body (sender_id=? AND created_at>?)
```

The SQLite docs call this cutting the number of binary searches in half. `count(*)` needs no column values, so it's covered whenever the filter is.

**The trade-off:** adding `body` copies every message text into the index. That doubles the storage for that column and makes every insert write more. Covering is a great deal for small columns (ids, timestamps, flags) on hot queries, and a poor one for large text.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "Index: `ON chat_members (user_id, joined_at)`. Table: `chat_members(chat_id, user_id, joined_at)` with a composite PRIMARY KEY, so it also has a rowid. Which query is answered by a **covering** index search?",
  "options": ["SELECT joined_at FROM chat_members WHERE user_id = ?", "SELECT chat_id FROM chat_members WHERE user_id = ?", "SELECT * FROM chat_members WHERE user_id = ?", "None: a covering index must include the primary key columns"], "answer": 0,
  "explanation": "joined_at and user_id are both in the index. chat_id isn't (here the rowid is a hidden column, not chat_id), so options 2 and 3 need a table lookup per row." }
```

## 5. Redundant indexes

If you have `(sender_id, created_at)`, a separate index on `(sender_id)` is redundant: any search on `sender_id` alone can use the leading column of the longer index. The SQLite docs' rule of thumb: **never keep two indexes where one is a prefix of the other; drop the shorter one.**

In a code review of a migration that adds a composite index, ask two questions:

1. Is the column order "equality columns, then range or sort column, then extra covered columns"?
2. Does an existing index become a prefix of the new one, so it can be dropped in the same migration?

```quiz
{ "id": "q5", "type": "choice", "label": "Application",
  "prompt": "A table has indexes `(a)`, `(a, b)`, `(b, a)` and `(a, b, c)`. Which can be dropped without making any search slower?",
  "options": ["(a) and (a, b)", "Only (a)", "(b, a)", "All except (a, b, c)"], "answer": 0,
  "explanation": "(a) and (a, b) are prefixes of (a, b, c), which serves every search they serve. (b, a) starts with b, so it's the only one that helps a filter on b alone." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "An orders page runs `SELECT id, total FROM orders WHERE customer_id = ? AND status = 'paid' ORDER BY created_at DESC LIMIT 20`. Propose one index and justify each column's position.",
  "model": "(customer_id, status, created_at), optionally with total at the end. customer_id and status are equality filters, so they lead (either order). created_at is the sort column, so it comes next and the rows come out sorted, letting LIMIT stop after 20. Adding total makes it covering, because id is the rowid. Check with EXPLAIN QUERY PLAN: SEARCH ... (customer_id=? AND status=?) and no USE TEMP B-TREE.",
  "explanation": "Equality columns first, then the sort column, then the columns you want covered." }
```

## 6. Your turn

Four hot queries from the messenger, at most three indexes, and no redundant ones. Work query by query: list the equality columns, the range or sort column, and the columns it reads. Then check each with EXPLAIN QUERY PLAN (your `explain()` from L01) before you run the tests.

```exercise
DB.M05.L02.E1
```
