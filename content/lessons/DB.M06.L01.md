---
{
  "id": "DB.M06.L01",
  "title": "Isolation levels, MVCC and locks: what the database promises",
  "difficulty": "intermediate",
  "minutes": 70,
  "prerequisites": ["DB.M05"],
  "objectives": [
    "Explain shared and exclusive locks with the Go sync.RWMutex analogy",
    "Define dirty read, non-repeatable read, phantom read, lost update and serialization anomaly, each with a messenger example",
    "Read the isolation-level table and name the defaults of PostgreSQL (Read Committed), MySQL InnoDB (Repeatable Read) and SQLite (serializable)",
    "Contrast lock-based concurrency (SQLite) with MVCC snapshots (PostgreSQL), and show from a runnable demo that SQLite never shows uncommitted data"
  ],
  "why": "You told me locks are where you struggle. Most concurrency bugs come from a wrong mental model of what the database guarantees, not from missing syntax. This lesson gives you the vocabulary and the model; the next three lessons reproduce the bugs and fix them in code.",
  "applications": [
    "Choosing an isolation level, or knowing why the default is enough, for a payment or counter feature",
    "Reading a 'could not serialize access' or 'database is locked' error and knowing what it means",
    "Explaining to a teammate why 'it's in a transaction' doesn't automatically make it safe"
  ],
  "exercises": [],
  "sources": [
    {
      "title": "PostgreSQL 18 Documentation: 13.2 Transaction Isolation",
      "url": "https://www.postgresql.org/docs/current/transaction-iso.html",
      "version": "PostgreSQL 18 (docs 18.7); not run on this machine",
      "verified": "2026-11-12",
      "claims": ["Definitions of dirty read, nonrepeatable read, phantom read and serialization anomaly", "Table of the four standard levels vs these phenomena; PostgreSQL's Read Uncommitted behaves like Read Committed and its Repeatable Read doesn't allow phantoms", "Read Committed is PostgreSQL's default", "Under Repeatable Read and Serializable, applications must be prepared to retry on serialization failure (SQLSTATE 40001)"]
    },
    {
      "title": "PostgreSQL 18 Documentation: 13.1 Introduction (MVCC)",
      "url": "https://www.postgresql.org/docs/current/mvcc-intro.html",
      "version": "PostgreSQL 18 (docs 18.7); not run on this machine",
      "verified": "2026-11-12",
      "claims": ["Each SQL statement sees a snapshot of the data", "In MVCC, reading never blocks writing and writing never blocks reading"]
    },
    {
      "title": "PostgreSQL 18 Documentation: 13.3 Explicit Locking",
      "url": "https://www.postgresql.org/docs/current/explicit-locking.html",
      "version": "PostgreSQL 18 (docs 18.7); not run on this machine",
      "verified": "2026-11-12",
      "claims": ["SELECT ... FOR UPDATE locks the retrieved rows against UPDATE, DELETE and other locking selects until the transaction ends", "Row-level locks don't affect plain queries", "PostgreSQL detects deadlocks and aborts one transaction; acquire locks in a consistent order"]
    },
    {
      "title": "MySQL 8.4 Reference Manual: 17.7.2.1 Transaction Isolation Levels",
      "url": "https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html",
      "version": "MySQL 8.4; not run on this machine",
      "verified": "2026-11-12",
      "claims": ["InnoDB's default isolation level is REPEATABLE READ", "Consistent reads in a transaction read the snapshot established by its first read"]
    },
    {
      "title": "Isolation In SQLite",
      "url": "https://www.sqlite.org/isolation.html",
      "version": "SQLite docs, page updated 2022-04-18; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["All SQLite transactions are serializable (except shared cache with read_uncommitted)", "SQLite serializes writes: one writer at a time", "A reader on another connection sees only committed transactions"]
    }
  ]
}
---
## 1. The same problem as a Go data race

In Go, two goroutines doing `counts[k]++` on one map is a data race. You fix it with a `sync.Mutex`, or with a `sync.RWMutex` when reads are common: **many readers may hold `RLock` at once, but `Lock` waits until nobody else holds either.**

A database has the same problem across processes: two HTTP requests, on two app servers, touching the same row. Databases use the same two kinds of lock:

| Lock | Go analogy | Many at once? | Blocks |
|---|---|---|---|
| **Shared (S)**, for reading | `RLock` | Yes | writers |
| **Exclusive (X)**, for writing | `Lock` | No, only one | readers and writers |

What differs between databases is **what** they lock (the whole database file, a table, a row, an index range) and **whether readers need a lock at all** (section 4).

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Connection A holds a shared lock on some data. Connection B asks for an exclusive lock on the same data. What happens, in the plain shared/exclusive model?",
  "options": ["B waits (or fails after a timeout) until A releases its shared lock", "B gets it immediately, because A is only reading", "A's lock is upgraded to exclusive", "Both get the lock and the last write wins"], "answer": 0,
  "explanation": "Exclusive is incompatible with shared, like Lock waiting for every RLock to be released in a Go RWMutex." }
```

## 2. What can go wrong: the anomalies

These are the names you'll see in docs, error messages and design reviews. Definitions follow the PostgreSQL docs; the examples are from our messenger.

- **Dirty read:** you read data written by a transaction that hasn't committed. *A's "delete chat" is still running and you already show the chat as gone; then A rolls back.*
- **Non-repeatable read:** you read a row twice in one transaction and get different values, because another transaction committed a change in between. *The unread count is 3, then 4, within one request.*
- **Phantom read:** you re-run a query with a WHERE condition and the **set of rows** changed. *"Members of chat 7" returns 5 users, then 6.*
- **Serialization anomaly:** the committed result can't be explained by running the transactions one at a time in *any* order.
- **Lost update:** two transactions read the same value, both compute a new value from it, and the second write silently overwrites the first. *Two likes arrive at once, and the counter goes from 10 to 11 instead of 12.* (L03 reproduces this one for real.)

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "Inside one transaction, a report counts the members of chat 7 (5 rows), then lists them, and gets 6 rows because someone joined and committed in between. Which anomaly is this?",
  "options": ["Phantom read", "Dirty read", "Lost update", "Non-repeatable read of one row"], "answer": 0,
  "explanation": "The set of rows matching the condition changed between two runs of the query. A non-repeatable read is about the value of a row you already read changing." }
```

## 3. Isolation levels: which anomalies are allowed

The SQL standard defines four isolation levels by which anomalies they allow. PostgreSQL's table (from its docs):

| Level | Dirty read | Non-repeatable read | Phantom read | Serialization anomaly |
|---|---|---|---|---|
| Read uncommitted | Allowed, but not in PG | Possible | Possible | Possible |
| Read committed | Not possible | Possible | Possible | Possible |
| Repeatable read | Not possible | Not possible | Allowed, but not in PG | Possible |
| Serializable | Not possible | Not possible | Not possible | Not possible |

The defaults you'll actually meet:

- **PostgreSQL: Read Committed.** Each statement sees data committed before *that statement* began.
- **MySQL InnoDB (your Go job): Repeatable Read.** Plain reads in a transaction see the snapshot taken by its first read.
- **SQLite: serializable.** Its docs say it achieves this "by actually serializing the writes": one writer at a time.

**Stronger isn't free.** Under Repeatable Read and Serializable, PostgreSQL may abort your transaction with a serialization failure (`could not serialize access due to concurrent update`, SQLSTATE `40001`). Its docs say applications **must be prepared to retry** the whole transaction. A higher level turns silent anomalies into errors you must handle.

The following is **not run on this machine (PostgreSQL unavailable); behaviour per the cited docs**:

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT unread_count FROM chat_members WHERE chat_id = 7 AND user_id = 42;
-- ... another transaction updates this row and commits ...
UPDATE chat_members SET unread_count = 0 WHERE chat_id = 7 AND user_id = 42;
-- ERROR:  could not serialize access due to concurrent update
ROLLBACK;  -- then retry the whole transaction from the start
```

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "PostgreSQL's default isolation level prevents non-repeatable reads.", "answer": false,
  "explanation": "The default is Read Committed: each statement sees what was committed before it started, so reading the same row twice in one transaction can give different values." }
```

## 4. Two ways to deliver isolation: locks or snapshots

**Locks (SQLite, rollback-journal mode).** SQLite has no row locks. It locks **the whole database file**, like one `RWMutex` around the entire database: many readers, or one writer committing. Simple and correct, but writers take turns (L02 shows the details).

**MVCC (PostgreSQL, and InnoDB for plain reads).** Multi-Version Concurrency Control keeps old versions of rows. Each statement reads a **snapshot**, so it doesn't need to wait for writers. The PostgreSQL docs: "reading never blocks writing and writing never blocks reading." Writers still lock the **rows** they change, so two writers to the same row wait for each other. You can take a row lock while reading with `SELECT ... FOR UPDATE`, which blocks other writers and lockers of those rows (not plain readers) until your transaction ends.

**Deadlocks:** when two transactions each wait for a lock the other holds, PostgreSQL detects it and aborts one of them. The docs' advice is to acquire locks in a consistent order (for example, always lock the lower id first).

Not run on this machine (PostgreSQL unavailable); behaviour per the cited docs:

```sql
BEGIN;
SELECT unread_count FROM chat_members WHERE chat_id = 7 AND user_id = 42 FOR UPDATE;
-- other transactions trying to UPDATE or SELECT ... FOR UPDATE this row now wait
UPDATE chat_members SET unread_count = unread_count + 1 WHERE chat_id = 7 AND user_id = 42;
COMMIT;  -- row lock released
```

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "In PostgreSQL, transaction A has run `SELECT ... FOR UPDATE` on message 5 and hasn't committed. Transaction B runs a plain `SELECT body FROM messages WHERE id = 5`. What happens to B?",
  "options": ["It returns immediately with the last committed version", "It waits until A commits", "It fails with a serialization error", "It returns A's uncommitted changes"], "answer": 0,
  "explanation": "Row-level locks block only writers and lockers of the same row. Plain reads use an MVCC snapshot and never wait for them." }
```

## 5. See it here: SQLite never shows uncommitted data

You can't run PostgreSQL here, but you can check the most basic promise, **no dirty reads**, with two SQLite connections to the same file:

```quiz
{ "id": "q5", "type": "output",
  "prompt": "Two connections share one database file. What does this print?",
  "code": "import os, sqlite3, tempfile\npath = os.path.join(tempfile.mkdtemp(), 'q.db')\nwriter = sqlite3.connect(path, isolation_level=None)\nreader = sqlite3.connect(path, isolation_level=None)\nwriter.execute('CREATE TABLE accounts (id INTEGER PRIMARY KEY, balance INTEGER)')\nwriter.execute('INSERT INTO accounts VALUES (1, 100)')\nwriter.execute('BEGIN')\nwriter.execute('UPDATE accounts SET balance = 0 WHERE id = 1')\nprint(reader.execute('SELECT balance FROM accounts').fetchone()[0])\nwriter.execute('COMMIT')\nprint(reader.execute('SELECT balance FROM accounts').fetchone()[0])",
  "answer": "100\n0",
  "explanation": "While the writer's transaction is open, its change is invisible to the other connection, which reads the committed 100. After COMMIT the reader sees 0. (isolation_level=None means Python adds no hidden BEGIN; you control transactions yourself. L02 explains why.)" }
```

One more thing that surprises everyone: SQLite is *serializable*, yet L03 will show it losing updates. How? **Isolation only protects what's inside one transaction.** If your code reads in one statement and writes in another, each runs as its own transaction, and the gap between them is unprotected. Keep that in mind; it's the core of this module.

```quiz
{ "id": "q6", "type": "explain", "label": "Explain",
  "prompt": "A teammate says: 'Our database is serializable, so concurrent requests can't corrupt the like counter.' The handler does SELECT likes, then in Python likes + 1, then UPDATE ... SET likes = ?, with autocommit on. Is the teammate right? Why or why not?",
  "model": "No. The isolation level applies within a transaction, but with autocommit the SELECT and the UPDATE are two separate transactions. Two requests can both read 10 and both write 11; each transaction is individually serializable, yet one like is lost. Fix it by doing the increment in one statement (likes = likes + 1), or by putting the read and write in one transaction that takes the write lock first.",
  "explanation": "Guarantees attach to transactions; a read-modify-write split across two transactions isn't protected." }
```
