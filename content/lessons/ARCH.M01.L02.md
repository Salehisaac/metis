---
{
  "id": "ARCH.M01.L02",
  "title": "Where transactions live: the unit of work",
  "difficulty": "intermediate",
  "minutes": 110,
  "prerequisites": ["ARCH.M01.L01"],
  "objectives": [
    "Put the transaction boundary around a whole use case in the service layer, and keep commits out of repositories",
    "Write a unit-of-work context manager that commits on success, rolls back on error and never swallows the exception",
    "Close a read-then-write race with a conditional UPDATE and rowcount",
    "Explain why committing in a FastAPI dependency after yield can report success for a write that failed, and choose a safer boundary",
    "Recognise when a 'transaction' crosses a service boundary and needs compensation instead of rollback"
  ],
  "why": "In your assessment the transaction questions scored lowest (A 0), and your Go code review found multi-step writes without a transaction and a cross-service delete with no compensation. Deciding where a transaction starts and ends is the most consequential layering decision you'll make: get it wrong and data is half-written exactly when something fails.",
  "applications": [
    "Money moves, stock reservations, bookings: any use case with two or more writes",
    "Running side effects (cache invalidation, events) only after a commit really happened",
    "Reviewing code for 'commit inside a helper' and swallowed rollbacks"
  ],
  "exercises": ["ARCH.M01.L02.E1"],
  "sources": [
    {
      "title": "Patterns of Enterprise Application Architecture catalog: Unit of Work",
      "url": "https://martinfowler.com/eaaCatalog/unitOfWork.html",
      "version": "Martin Fowler, PoEAA online catalog (undated page)",
      "verified": "2026-11-12",
      "claims": ["A unit of work maintains a list of objects affected by a business transaction and coordinates writing out the changes"]
    },
    {
      "title": "Patterns of Enterprise Application Architecture catalog: Service Layer",
      "url": "https://martinfowler.com/eaaCatalog/serviceLayer.html",
      "version": "Martin Fowler, PoEAA online catalog (undated page)",
      "verified": "2026-11-12",
      "claims": ["The service layer controls transactions in the implementation of its operations"]
    },
    {
      "title": "sqlite3: How to use the connection context manager",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["with conn: commits if the body finishes without an exception and rolls back if it raises", "The context manager neither opens a new transaction nor closes the connection", "In the default legacy mode a transaction is opened implicitly before INSERT, UPDATE, DELETE or REPLACE"]
    },
    {
      "title": "The Python Language Reference: 3.3.9 With Statement Context Managers",
      "url": "https://docs.python.org/3.12/reference/datamodel.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["__exit__ receives three None arguments when the block ends without an exception", "Returning a true value from __exit__ suppresses the exception", "__exit__ should not re-raise the passed-in exception"]
    },
    {
      "title": "FastAPI docs: Dependencies with yield",
      "url": "https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/",
      "version": "FastAPI docs (no version on page); behaviour run locally with fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["Normally the exit code of a dependency with yield runs after the response is sent", "Depends(scope=\"function\") ends the dependency after the path operation function, before the response is sent", "A dependency with yield defaults to scope \"request\""]
    },
    {
      "title": "microservices.io: Pattern: Saga",
      "url": "https://microservices.io/patterns/data/saga.html",
      "version": "microservices.io (Chris Richardson), undated page",
      "verified": "2026-11-12",
      "claims": ["A transaction that spans services is implemented as a sequence of local transactions", "Completed steps are undone by compensating transactions", "A drawback is the lack of automatic rollback"]
    }
  ]
}
---
## 1. Who says "commit"?

A use case like "borrow a book" is two writes: take one copy off the shelf, and record the loan. Either both happen or neither. That's what a transaction is for. The question for this lesson is **which code ends it.**

Here's the tempting version: each repository method commits its own write, "so nothing gets lost".

```python
class CommittingLoanRepo:
    def __init__(self, conn):
        self.conn = conn

    def take_copy(self, book_id):
        self.conn.execute("UPDATE books SET available = available - 1 WHERE id = ?", (book_id,))
        self.conn.commit()

    def record_loan(self, book_id, member):
        if not member:
            raise ValueError("member required")  # stands in for any crash between the two writes
        self.conn.execute("INSERT INTO loans VALUES (?, ?)", (book_id, member))
        self.conn.commit()
```

Borrow a book with a bad member name, then try to roll back (one copy on the shelf to start):

```console
$ python loans.py
failed: member required
after rollback: available=0 loans=0
```

The copy is gone and there's no loan. The rollback came too late: the first write was already committed, so nothing could undo it. A crash at that point (the process killed, the second statement failing) behaves the same way: **the committed statement stays, the uncommitted one disappears.** Nothing "finishes both".

**The rule:** a repository runs statements and never commits. The transaction belongs to the **use case**, and use cases live in the service layer. Fowler's catalog says the service layer controls transactions in the implementation of its operations, and names the pattern that tracks one business transaction's changes and writes them out together: the **unit of work**.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "`place_order` calls `orders.insert(...)`, then `stock.decrement(...)`, then `payments.charge_record(...)`. Where should the single commit happen?",
  "options": ["At the end of each repository method", "In `place_order`, after all three calls succeed", "In the endpoint, after `place_order` returns", "In a database trigger"], "answer": 1,
  "explanation": "The service operation is the unit of work: it knows when the whole use case succeeded. Committing per method leaves partial orders on failure. The endpoint option can work, but it puts a business decision in the HTTP layer (and section 4 shows the trap in FastAPI)." }
```

## 2. A unit of work in Python

A unit of work is a context manager: open the transaction on entry, commit if the block finished, roll back if it raised. sqlite3's connection already behaves this way with `with conn:`, so the smallest version just wraps it and hands out the repositories:

```python
from contextlib import contextmanager


class OutOfCopies(Exception):
    pass


class LoanRepo:
    """No commits in here: the caller decides when the unit of work ends."""

    def __init__(self, conn):
        self.conn = conn

    def take_copy(self, book_id) -> bool:
        cur = self.conn.execute(
            "UPDATE books SET available = available - 1 WHERE id = ? AND available > 0", (book_id,)
        )
        return cur.rowcount == 1

    def record_loan(self, book_id, member):
        if not member:
            raise ValueError("member required")
        self.conn.execute("INSERT INTO loans VALUES (?, ?)", (book_id, member))


@contextmanager
def unit_of_work(conn):
    with conn:  # sqlite3: commit if the block succeeds, roll back if it raises
        yield LoanRepo(conn)


def borrow(conn, book_id, member):
    with unit_of_work(conn) as loans:
        if not loans.take_copy(book_id):
            raise OutOfCopies(book_id)
        loans.record_loan(book_id, member)
```

Three borrow attempts on a book with one copy:

```console
$ python loans_uow.py
'': ValueError, available=1 loans=0
'sara': ok, available=0 loans=1
'omid': OutOfCopies, available=0 loans=1
```

The failed first attempt left the copy on the shelf. Note that `OutOfCopies` is raised **inside** the `with` block. That's what triggers the rollback. Raise it after the block and the transaction has already committed.

If you write the unit of work as a class, Python calls `__exit__(exc_type, exc, tb)` when the block ends. The language reference says all three are `None` when there was no exception, and that **returning a true value suppresses the exception**. That makes one line in `__exit__` very dangerous:

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "class Tx:\n    def __enter__(self):\n        print(\"begin\")\n        return self\n\n    def __exit__(self, exc_type, exc, tb):\n        print(\"rollback\" if exc_type else \"commit\")\n        return True\n\ntry:\n    with Tx():\n        raise KeyError(\"order 7\")\n    print(\"after\")\nexcept KeyError:\n    print(\"caught\")",
  "answer": "begin\nrollback\nafter",
  "explanation": "`return True` swallows the KeyError, so execution continues after the with block and the caller never learns the use case failed. That's a swallowed error, the Python twin of `authors, _ := ...`. Return False (or nothing) so the exception propagates after the rollback." }
```

## 3. Read-then-write races: let the database check

In `take_copy` the "is there a copy left?" check is part of the `UPDATE` itself (`AND available > 0`), and `rowcount` says whether a row changed. Compare that with reading first and deciding in Python:

```python
row = conn.execute("SELECT available FROM books WHERE id = ?", (1,)).fetchone()
if row[0] > 0:                      # two requests can both get here with available = 1
    conn.execute("UPDATE books SET available = available - 1 WHERE id = ?", (1,))
```

Two concurrent requests can both read `1` and both decrement, which gives `-1` copies. Your Go review flagged this exact "read-then-write" shape. A conditional write makes the check and the change one atomic statement:

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\n\nconn = sqlite3.connect(\":memory:\")\nconn.execute(\"CREATE TABLE seats (id INTEGER PRIMARY KEY, free INTEGER)\")\nconn.execute(\"INSERT INTO seats VALUES (1, 1)\")\nfor _ in range(3):\n    cur = conn.execute(\"UPDATE seats SET free = free - 1 WHERE id = 1 AND free > 0\")\n    print(cur.rowcount, end=\" \")\nprint(conn.execute(\"SELECT free FROM seats\").fetchone()[0])",
  "answer": "1 0 0 0",
  "explanation": "The first UPDATE matches the row and changes it (rowcount 1). After that `free > 0` is false, so the row doesn't match and rowcount is 0. The count never goes below zero, however many requests race." }
```

Other tools for the same job: a `UNIQUE` or `CHECK` constraint (let the insert fail, then map `IntegrityError` to a domain error), or row locks such as `SELECT ... FOR UPDATE` on PostgreSQL/MySQL. Prefer the constraint or the conditional write when they fit. They need no extra round trip.

## 4. The FastAPI trap: committing after `yield`

WEB.M05 showed the "session per request" pattern: a dependency with `yield` that commits after the endpoint returns. It's simple, and for many CRUD apps it's fine. But check *when* that commit runs. FastAPI's docs say the exit code of a dependency with `yield` normally runs **after the response is sent**. So what does the client see if the commit fails?

```python
def get_session():
    yield "session"
    raise RuntimeError("commit failed: disk full")  # what a failing commit after yield looks like


def get_session_fn():
    yield "session"
    raise RuntimeError("commit failed: disk full")


@app.post("/request-scope")
def a(s: Annotated[str, Depends(get_session)]):
    return {"saved": True}


@app.post("/function-scope")
def b(s: Annotated[str, Depends(get_session_fn, scope="function")]):
    return {"saved": True}
```

```console
$ python commit_after.py        # TestClient(app, raise_server_exceptions=False), FastAPI 0.162.0
/request-scope 200 {"saved":true}
/function-scope 500 Internal Server Error
```

With the default scope, the client was told `{"saved": true}` for a write that never committed. `Depends(..., scope="function")` ends the dependency **before** the response is sent (the docs describe both scopes), so the failure turns into a 500. Better still, let the service own the transaction: the service knows the use case finished, it commits, and only then does the endpoint build the response.

| Where the commit lives | Good | Watch out |
|---|---|---|
| Dependency, default scope | One line for every endpoint | Commit runs after the response; a failed commit can still look like success |
| Dependency, `scope="function"` | Commit errors reach the client | Still one transaction per request, even when a request should do two |
| Service (unit of work) | Boundary matches the use case; side effects can run after the commit | Each service function must open it (that's the point) |

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "A dependency commits after `yield` (default scope). The commit fails because of a constraint violation. What does the client most likely receive, on FastAPI 0.162?",
  "options": ["The endpoint's normal success response", "500 Internal Server Error", "409 Conflict", "No response at all"], "answer": 0,
  "explanation": "By default the code after yield runs after the response is sent, so the success response has already gone out. Use scope=\"function\" or commit in the service before returning." }
```

## 5. When there's no transaction to use

A transaction only covers **one database**. Your Go system deletes across several services in sequence, with no compensation if a later step fails. No `with` block can fix that, because each service commits its own database.

The options, in order of preference:

1. **Don't split it.** If the data must change together, maybe it belongs to one service and one database.
2. **Make each step a local transaction and plan the undo.** microservices.io calls this a **saga**: a sequence of local transactions, where completed steps are undone by *compensating* transactions if a later one fails. Its listed drawback is the "lack of automatic rollback": you write the undo yourself.
3. **Record the intent in your own transaction and let a worker finish it.** That's the transactional outbox in ARCH.M03.

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "If `delete_user` calls the profile service's RPC and then deletes the local row inside `with conn:`, a failure of the local delete also undoes the RPC's delete.", "answer": false,
  "explanation": "The rollback covers only this connection's writes. The other service already committed its own. You need a compensating step (or a design that avoids the split)." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Design review",
  "prompt": "A PR adds `def save(self): self.conn.commit()` to a `ReportRepo` and calls it after every insert, 'so a crash never loses data'. The report job inserts 5,000 rows per run. Review it.",
  "model": "Committing per row turns one job into 5,000 transactions. A crash halfway leaves a half-written report that looks complete to readers, and a rerun duplicates the first half. It's also much slower, because each commit waits for the disk. The job is one unit of work: commit once at the end (or in explicit batches with a checkpoint that makes reruns idempotent). The repository shouldn't commit at all; the job's service code owns the boundary.",
  "explanation": "'Commit early' trades a clean failure (nothing written) for a messy one (part written)." }
```

## 6. Your turn: a transfer that can't half-happen

The exercise is a wallet transfer: withdraw from one account, deposit into another. You write the unit of work, a conditional `withdraw`, and the service function. One repository method that's already written breaks the all-or-nothing rule; a test will point at it.

```exercise
ARCH.M01.L02.E1
```
