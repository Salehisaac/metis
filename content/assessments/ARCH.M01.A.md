---
{ "id": "ARCH.M01.A", "module": "ARCH.M01", "title": "ARCH.M01 module assessment: layering and boundaries", "minutes": 20 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. The explain questions are reviewed with the mentor: they're the evidence for "decide where transactions live and justify it".

```quiz
{ "id": "a1", "type": "choice",
  "prompt": "Which line belongs in the repository layer?",
  "options": ["`raise HTTPException(404, \"order not found\")`", "`if order.total > customer.credit_limit: raise CreditExceeded()`", "`conn.execute(\"SELECT id, total FROM orders WHERE id = ?\", (order_id,))`", "`return JSONResponse(status_code=201, content=...)`"], "answer": 2,
  "explanation": "SQL is the repository's job. The credit rule belongs in the service, and the HTTP exception and response belong in the API layer." }
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\n\nconn = sqlite3.connect(\":memory:\")\nconn.execute(\"CREATE TABLE t (n INTEGER)\")\n\ndef add(n):\n    conn.execute(\"INSERT INTO t VALUES (?)\", (n,))\n    conn.commit()\n\ntry:\n    with conn:\n        add(1)\n        add(2)\n        raise RuntimeError(\"step 3 failed\")\nexcept RuntimeError:\n    pass\nprint(conn.execute(\"SELECT COUNT(*) FROM t\").fetchone()[0])",
  "answer": "2",
  "explanation": "`add` commits each row itself, so by the time the block raises there's nothing left to roll back. The `with conn:` boundary is meaningless when a helper inside it commits." }
```

```quiz
{ "id": "a3", "type": "truefalse",
  "prompt": "A unit of work's `__exit__` that ends with `return True` after rolling back is safe, because the data is consistent.", "answer": false,
  "explanation": "The data is consistent, but returning True suppresses the exception: the caller thinks the use case succeeded. Roll back, then let the exception propagate." }
```

```quiz
{ "id": "a4", "type": "choice",
  "prompt": "Two requests run `SELECT seats_left` (both read 1) and then `UPDATE events SET seats_left = seats_left - 1`. What's the best fix?",
  "options": ["Add `time.sleep` between the two statements", "One statement: `UPDATE ... SET seats_left = seats_left - 1 WHERE id = ? AND seats_left > 0`, then check rowcount", "Cache seats_left in Redis", "Catch the exception and retry"], "answer": 1,
  "explanation": "The conditional write makes check-and-change atomic, so the second request changes 0 rows and you can report 'full'." }
```

```quiz
{ "id": "a5", "type": "explain", "label": "Design review",
  "prompt": "An endpoint `POST /orders` does: insert the order, decrement stock, then call the email service to send a confirmation, all inside one service function wrapped in a unit of work. The email call is slow and sometimes times out, which rolls back the order. Where should the transaction boundary be, and what happens to the email?",
  "model": "The transaction should cover only the database writes (order plus stock), so a failing email can't undo a valid order. Commit first, then trigger the email. The email isn't part of the atomic unit, and it can't be rolled back anyway. Either send it after the commit (accepting it may be lost on a crash) or record an 'email pending' row in the same transaction and let a worker send it with retries (the outbox, ARCH.M03). Never hold a database transaction open while waiting on a slow external call.",
  "explanation": "Transactions cover what the database can undo. Side effects go after the commit, or into an outbox." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Design review",
  "prompt": "A teammate proposes an `INotificationSender` Protocol with one implementation (`SmtpSender`) for a feature that sends one email type. Tests currently patch nothing and don't send email. Would you accept it? What would change your answer?",
  "model": "Not as a speculative interface on its own merit: one implementation and no consumer that swaps it means it's a presumptive abstraction with a carrying cost. What would change my answer is a real need: tests that must assert 'an email was sent' without SMTP. Then a small Protocol declared at the service, plus an in-memory fake used by those tests, is justified, because email is an external side effect. In that case keep it to the one method the service calls.",
  "explanation": "A seam earns its place through a second implementation or a test need that exists now." }
```
