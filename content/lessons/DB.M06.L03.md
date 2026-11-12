---
{
  "id": "DB.M06.L03",
  "title": "Lost updates: reproduce them, then fix them",
  "difficulty": "intermediate",
  "minutes": 75,
  "prerequisites": ["DB.M06.L02"],
  "objectives": [
    "Reproduce a lost update deterministically with two connections, and statistically with threads",
    "Fix it with a single atomic UPDATE ... SET x = x + 1 and use cursor.rowcount instead of a pre-check SELECT",
    "Fix read-modify-write logic that can't be one statement with BEGIN IMMEDIATE",
    "Explain why a test that passes once doesn't prove concurrent code is correct"
  ],
  "why": "This is the module's core outcome: reproduce and fix a lost update. Counters, balances, stock levels and 'seats left' all have this bug when the code reads a value into the app and writes back a new one. It passes every single-user test, which is exactly why it reaches production.",
  "applications": [
    "Like counters, unread counters, view counts",
    "Wallet balances and inventory (with a CHECK that it never goes negative)",
    "Reviewing ORM code that loads an object, changes a field and saves it"
  ],
  "exercises": ["DB.M06.L03.E1"],
  "sources": [
    {
      "title": "Isolation In SQLite",
      "url": "https://www.sqlite.org/isolation.html",
      "version": "SQLite docs, page updated 2022-04-18; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["SQLite transactions are serializable; writes are serialized, one writer at a time"]
    },
    {
      "title": "Transaction (BEGIN, COMMIT, ROLLBACK)",
      "url": "https://www.sqlite.org/lang_transaction.html",
      "version": "SQLite docs, page updated 2026-02-18; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["A statement run outside an explicit transaction runs in its own automatically committed transaction", "BEGIN IMMEDIATE starts a write transaction immediately"]
    },
    {
      "title": "sqlite3: DB-API 2.0 interface for SQLite databases",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (installed 3.12.3, SQLite 3.45.1)",
      "verified": "2026-11-12",
      "claims": ["Cursor.rowcount is the number of modified rows for INSERT, UPDATE, DELETE and REPLACE", "set_trace_callback is invoked for each SQL statement actually executed, including the module's own transaction statements"]
    },
    {
      "title": "PostgreSQL 18 Documentation: 13.2 Transaction Isolation",
      "url": "https://www.postgresql.org/docs/current/transaction-iso.html",
      "version": "PostgreSQL 18 (docs 18.7); not run on this machine",
      "verified": "2026-11-12",
      "claims": ["In Read Committed, an UPDATE that finds its target row changed by a concurrent transaction waits for it to commit and re-evaluates its WHERE clause on the updated row"]
    }
  ]
}
---
## 1. The bug in four lines

A message's like counter, written the "obvious" way:

```python
likes = conn.execute("SELECT likes FROM messages WHERE id = 1").fetchone()[0]
conn.execute("UPDATE messages SET likes = ? WHERE id = 1", (likes + 1,))
```

It's Go's `v := m[k]; m[k] = v + 1` from two goroutines. The value lives in your program between the read and the write, and nothing stops someone else from changing the row in that gap.

Reproduce it **deterministically** with two connections (two app servers handling two requests), interleaving the steps by hand:

```python
alice = sqlite3.connect(DB, isolation_level=None)   # two app servers / two requests
bob = sqlite3.connect(DB, isolation_level=None)

a = alice.execute("SELECT likes FROM messages WHERE id = 1").fetchone()[0]
b = bob.execute("SELECT likes FROM messages WHERE id = 1").fetchone()[0]
print("alice read", a, "| bob read", b)
alice.execute("UPDATE messages SET likes = ? WHERE id = 1", (a + 1,))
bob.execute("UPDATE messages SET likes = ? WHERE id = 1", (b + 1,))
print("likes now:", setup.execute("SELECT likes FROM messages WHERE id = 1").fetchone()[0])
```

```console
alice read 0 | bob read 0
likes now: 1
```

Two likes, counter at 1. No error, no warning. Every statement was correct and individually serializable; each ran in its own autocommitted transaction, and the **read-modify-write spanned two of them**.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "Same interleaving, three requests this time. What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:', isolation_level=None)\nconn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY, views INTEGER)')\nconn.execute('INSERT INTO posts VALUES (1, 10)')\nreads = [conn.execute('SELECT views FROM posts WHERE id = 1').fetchone()[0] for _ in range(3)]\nfor v in reads:\n    conn.execute('UPDATE posts SET views = ? WHERE id = 1', (v + 1,))\nprint(conn.execute('SELECT views FROM posts WHERE id = 1').fetchone()[0])",
  "answer": "11",
  "explanation": "All three 'requests' read 10 before anyone wrote, so each writes 11. Two of the three views are lost." }
```

## 2. Under real concurrency: sometimes

Four threads, each with its own connection and a 10 s busy timeout, each liking the message 200 times (800 likes in total):

```python
def like_read_modify_write(conn):
    likes = conn.execute("SELECT likes FROM messages WHERE id = 1").fetchone()[0]
    conn.execute("UPDATE messages SET likes = ? WHERE id = 1", (likes + 1,))

def like_atomic(conn):
    conn.execute("UPDATE messages SET likes = likes + 1 WHERE id = 1")
```

`hammer(like)` resets the table, starts the 4 threads and returns the final count. Two runs on this machine:

```console
read-modify-write: 210 of 800
atomic UPDATE:     800 of 800
read-modify-write: 658 of 800
atomic UPDATE:     800 of 800
```

Two things to take away:

- The broken version lost a **different** number each run (590, then 142). Concurrency bugs are timing-dependent. On a quiet laptop, with one user clicking, it might lose nothing for weeks. **A passing test doesn't prove concurrent code correct**; a deterministic interleaving (section 1) or a reasoned argument does.
- The one-statement version was exact both times.

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "If the threaded test of the read-modify-write version happens to print 800 of 800, the code is correct.", "answer": false,
  "explanation": "The loss depends on how the threads interleave. One lucky run proves nothing; the two-connection interleaving in section 1 shows the bug every time." }
```

## 3. Fix 1: let the database do the arithmetic

```sql
UPDATE messages SET likes = likes + 1 WHERE id = ?
```

The database reads the current value and writes the new one **inside one statement**, while it holds the write lock. There's no gap for another writer. This is the fix to reach for first: shortest lock time, one round trip, no retries.

It also works for conditional changes. "Take one seat if any are left" is one statement:

```python
cur = conn.execute("UPDATE events SET seats_left = seats_left - 1 WHERE id = ? AND seats_left > 0", (event_id,))
if cur.rowcount == 0:
    ...  # sold out, or no such event
```

`cursor.rowcount` is the number of rows the UPDATE changed. It replaces the "SELECT first to check" step, which was itself a race: the check could pass, and the value change before your UPDATE.

In PostgreSQL the same statement is safe for the same reason: in Read Committed, an UPDATE that finds its row changed by a concurrent transaction waits for that transaction, then re-checks its WHERE clause against the new row version (not run here; behaviour per the cited docs).

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:', isolation_level=None)\nconn.execute('CREATE TABLE events (id INTEGER PRIMARY KEY, seats_left INTEGER)')\nconn.execute('INSERT INTO events VALUES (1, 1)')\nsql = 'UPDATE events SET seats_left = seats_left - 1 WHERE id = ? AND seats_left > 0'\nprint(conn.execute(sql, (1,)).rowcount, conn.execute(sql, (1,)).rowcount, conn.execute(sql, (2,)).rowcount)",
  "answer": "1 0 0",
  "explanation": "The first call takes the last seat (1 row changed). The second finds seats_left = 0, so the WHERE matches nothing. Event 2 doesn't exist. rowcount = 0 covers both 'sold out' and 'not found'; check existence separately only if you must tell them apart." }
```

## 4. Fix 2: when the logic can't be one statement, lock first

Sometimes the new value needs real Python between the read and the write: a rule you can't write in SQL, or a call to another function. Then put both steps in **one transaction that takes the write lock before reading**, exactly what L02's BEGIN IMMEDIATE does:

```python
def like_immediate(conn):
    conn.execute("BEGIN IMMEDIATE")          # take the write lock BEFORE reading
    try:
        likes = conn.execute("SELECT likes FROM messages WHERE id = 1").fetchone()[0]
        conn.execute("UPDATE messages SET likes = ? WHERE id = 1", (likes + 1,))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
```

```console
BEGIN IMMEDIATE:   800 of 800
```

Correct, but every like now holds the database's only write lock across two statements and some Python. Keep the gap tiny. A plain deferred `BEGIN` wouldn't be enough: two transactions could both read (SHARED) and then hit L02's upgrade trap, failing instead of losing the update, which is better but still not done.

In PostgreSQL the equivalent is `SELECT ... FOR UPDATE` inside the transaction, which locks just that row (L01; not run here).

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "Which change fixes the lost update in `x = SELECT balance; if x >= amount: UPDATE accounts SET balance = x - amount` and is the simplest?",
  "options": ["UPDATE accounts SET balance = balance - ? WHERE id = ? AND balance >= ?, then check rowcount", "Wrap the two statements in a plain BEGIN ... COMMIT", "Add time.sleep() between the statements", "Run the SELECT twice and compare"], "answer": 0,
  "explanation": "The condition and the arithmetic both fit in one UPDATE, and rowcount tells you whether it applied. A plain deferred BEGIN can still fail at the upgrade; sleeping just changes the timing." }
```

```quiz
{ "id": "q5", "type": "choice", "label": "Debugging",
  "prompt": "An ORM handler does `msg = session.get(Message, id); msg.likes += 1; session.commit()`. Under load, likes go missing. What's happening?",
  "options": ["It's a read-modify-write: the ORM reads likes, Python adds 1, and the UPDATE writes a fixed number back", "The ORM caches the commit", "SQLAlchemy doesn't support integers", "The session is not thread-safe, so it skips commits"], "answer": 0,
  "explanation": "The ORM hides the SELECT and the UPDATE, but it's the same pattern as section 1: the UPDATE sends the computed value (like likes = 11), not likes + 1. The fix is the same: send the arithmetic as SQL, e.g. SQLAlchemy's update(Message).values(likes=Message.likes + 1) (DB.M07)." }
```

## 5. Your turn

The exercise's unread counters have this exact bug, twice: once for a single member, once in a loop over all members when a message arrives. The tests trace the SQL your functions send (with `set_trace_callback`) and run four threads at once. Fix it the section 3 way.

```exercise
DB.M06.L03.E1
```

```quiz
{ "id": "q6", "type": "explain", "label": "Explain",
  "prompt": "In two or three sentences: why did the read-modify-write like counter lose updates even though SQLite says all its transactions are serializable?",
  "model": "With autocommit each statement is its own transaction. The SELECT and the UPDATE were two separate (individually serializable) transactions, so another connection could read the same old value between them and both wrote old + 1. Serializability protects what's inside one transaction, not a sequence of them.",
  "explanation": "Isolation guarantees are per transaction." }
```
