---
{
  "id": "ARCH.M03.L03",
  "title": "Idempotent consumers, retries and backoff",
  "difficulty": "advanced",
  "minutes": 110,
  "prerequisites": ["ARCH.M03.L02"],
  "objectives": [
    "Make a message consumer idempotent with a processed-messages key committed in the same transaction as the effect",
    "Tell naturally idempotent operations from ones that need deduplication",
    "Design an HTTP idempotency key: what is stored, what a retry returns",
    "Write a retry policy: transient errors only, exponential backoff with a cap and jitter, a maximum number of attempts, at one layer"
  ],
  "why": "At-least-once delivery (L02, Kafka's default) means duplicates are normal, not exceptional. You named idempotency in your assessment answers; this lesson turns the word into a mechanism you can implement and test, and pairs it with retries, because a retry is just a duplicate you sent on purpose.",
  "applications": [
    "Kafka or RabbitMQ consumers that change money, stock or counters",
    "Payment and order endpoints that clients (or proxies) may retry",
    "Calling flaky third-party APIs without amplifying an outage"
  ],
  "exercises": ["ARCH.M03.L03.E1"],
  "sources": [
    {
      "title": "microservices.io: Pattern: Idempotent Consumer",
      "url": "https://microservices.io/patterns/communication-style/idempotent-consumer.html",
      "version": "microservices.io (Chris Richardson), undated page",
      "verified": "2026-11-12",
      "claims": ["A consumer must be idempotent: processing the same message repeatedly has the same outcome as processing it once", "After starting the transaction, the handler inserts the message id into a PROCESSED_MESSAGE table; the insert fails if the message was already processed", "The table's primary key is (subscriberId, messageID)"]
    },
    {
      "title": "Patterns of Distributed Systems: Idempotent Receiver",
      "url": "https://martinfowler.com/articles/patterns-of-distributed-systems/idempotent-receiver.html",
      "version": "Unmesh Joshi, martinfowler.com (Patterns of Distributed Systems)",
      "verified": "2026-11-12",
      "claims": ["Servers get duplicate requests when clients retry after a lost response", "Identify each client uniquely and track its request numbers; return the saved response for a request already processed"]
    },
    {
      "title": "Timeouts, retries, and backoff with jitter",
      "url": "https://builder.aws.com/content/3EumjoZascWd1oZiEgL8ORlv3qE/timeouts-retries-and-backoff-with-jitter",
      "version": "Amazon Builders' Library article (2019), now hosted on AWS Builder Center",
      "verified": "2026-11-12",
      "claims": ["Retries are selfish; when failures are caused by overload, retries can make matters worse", "Exponential backoff increases the wait after every attempt; implementations cap it and limit the number of retries", "Jitter adds randomness to spread retries in time", "Retrying at every layer multiplies load (example: 243x for five layers of three retries); retry at a single point", "Idempotent APIs make retries safe; some APIs provide token-based idempotency"]
    },
    {
      "title": "Apache Kafka documentation: Message Delivery Semantics",
      "url": "https://kafka.apache.org/44/design/design/",
      "version": "Apache Kafka 4.4 docs",
      "verified": "2026-11-12",
      "claims": ["A consumer that crashes after processing but before saving its position reprocesses messages: at-least-once"]
    }
  ]
}
---
## 1. Duplicates are normal

Where duplicates come from in a system like yours:

- The outbox relay crashed between publishing and marking (L02).
- A Kafka consumer processed a message and crashed before saving its offset. Kafka's docs describe exactly this as at-least-once: the replacement consumer receives messages that were already processed.
- A client timed out and retried, but the first request actually succeeded.

So the consumer must be **idempotent**. microservices.io defines it as: "the outcome of processing the same message repeatedly must be the same as processing the message once."

A loyalty service awards points when it sees an order event. The naive consumer, given the same message twice:

```python
def award_naive(msg):
    with conn:
        conn.execute("UPDATE members SET points = points + ? WHERE id = ?", (msg["points"], msg["member_id"]))
```

```console
$ python points.py        # first line
naive: 100
```

A 50-point order paid out 100.

## 2. The processed-messages key

The fix from the idempotent-consumer pattern: in the **same transaction** as the effect, insert the message id into a table whose primary key rejects repeats. microservices.io: "the INSERT will fail if the message has been already processed successfully".

```python
conn.executescript("""
    CREATE TABLE inbox (                       -- messages this consumer has already handled
        consumer TEXT NOT NULL,
        message_id TEXT NOT NULL,
        PRIMARY KEY (consumer, message_id)
    );
""")


def award_idempotent(msg):
    with conn:
        try:
            conn.execute("INSERT INTO inbox VALUES ('loyalty', ?)", (msg["id"],))
        except sqlite3.IntegrityError:
            return "duplicate, skipped"
        conn.execute("UPDATE members SET points = points + ? WHERE id = ?", (msg["points"], msg["member_id"]))
        return "applied"
```

```console
$ python points.py        # last two lines
['applied', 'duplicate, skipped']
idempotent: 50
```

Three details make or break it:

1. **Same transaction.** Marker without effect (separate commits, crash in between) loses the points forever. Effect without marker doubles them on redelivery.
2. **The database detects the duplicate**, through the primary key. A `SELECT ... WHERE message_id = ?` check first is a read-then-write race (ARCH.M01.L02) when two deliveries are handled at once.
3. **The key includes the consumer.** The pattern's table has the primary key `(subscriberId, messageID)`: the loyalty service and the email service both legitimately process the same event.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "A consumer inserts the message id into `processed` and commits, then applies the effect in a second transaction. It crashes between the two. What happens on redelivery?",
  "options": ["The effect is applied, since the message is redelivered", "The message is skipped as a duplicate and its effect is never applied", "The effect is applied twice", "The broker detects the crash and discards the message"], "answer": 1,
  "explanation": "The marker says 'done' but the work never happened. Marker and effect must commit together, or the marker turns at-least-once into at-most-once." }
```

## 3. Naturally idempotent operations

Some writes are idempotent without any table:

| Operation | Idempotent? |
|---|---|
| `UPDATE orders SET status = 'shipped' WHERE id = 7` | Yes: same result every time |
| `DELETE FROM carts WHERE user_id = 3` | Yes |
| `INSERT ... ON CONFLICT (order_id) DO NOTHING` with a natural unique key | Yes |
| `UPDATE members SET points = points + 50` | No |
| `INSERT INTO payments (...)` without a unique business key | No |
| Sending an email, calling a webhook | No, and it can't be undone |

Prefer designs where the effect is naturally idempotent ("set status to paid", "upsert by payment id"). Add a processed-messages table when it isn't.

Watch the last row: if the effect is an external call (email, payment provider), the marker can't share a transaction with it. Record "sent" in the database after the call succeeds and accept rare duplicates, or pass an **idempotency key** to the provider so *it* deduplicates.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "Each handler receives the same message 3 times. What does this print?",
  "code": "order = {\"status\": \"new\", \"items\": 0}\n\ndef mark_shipped(msg):\n    order[\"status\"] = \"shipped\"\n\ndef add_item(msg):\n    order[\"items\"] += msg[\"qty\"]\n\nmsg = {\"id\": \"e-1\", \"qty\": 2}\nfor _ in range(3):\n    mark_shipped(msg)\n    add_item(msg)\nprint(order)",
  "answer": "{'status': 'shipped', 'items': 6}",
  "explanation": "Setting a status is naturally idempotent: three deliveries, same result. Adding a quantity isn't: three deliveries triple it. add_item needs deduplication by message id (or a design that sets an absolute value)." }
```

## 4. Idempotency keys over HTTP

Your assessment answer said PUT is idempotent. For `POST /payments`, a retry after a timeout is dangerous: did the first one go through? Fowler's *Idempotent Receiver* pattern describes the server side: identify the client's request uniquely, and if a request with that identity "is already processed", return the **saved response** instead of running it again.

Over HTTP this is usually a client-generated `Idempotency-Key` header:

1. In the same transaction as the payment, store `(key, response body, status)`.
2. A retry with the same key returns the stored response, and nothing is charged twice.
3. Keep keys for a limited time (a day, say) and reject a key reused with a *different* body.

ARCH.M04's booking exercise uses this shape.

## 5. Retries without making it worse

Retrying a failed call is how you survive blips. The AWS Builders' Library article on retries starts with a warning: retries are "selfish". They spend more of the server's capacity on your request, and "when failures are caused by overload, retries that increase load can make matters significantly worse." So every retry policy has the same parts:

- **Retry only transient errors**: timeouts, connection resets, 503. A 400 or a `ValueError` will fail the same way next time.
- **Exponential backoff**: "the wait time is increased exponentially after every attempt", 0.5 s, 1 s, 2 s, ...
- **A cap**: implementations "cap their backoff to a maximum value", and they also "limit the number of times that the client retries".
- **Jitter**: "Jitter adds some amount of randomness to the backoff to spread the retries around in time", so a thousand clients that failed together don't retry together.
- **One layer**: the article's example shows retries at every layer of a five-deep call chain multiplying database load 243x. Pick one place to retry.
- **Idempotency**: a retry is a deliberate duplicate. Only retry operations that are idempotent, or that carry an idempotency key.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "base, cap = 0.25, 5.0\nprint([min(cap, base * 2 ** (n - 1)) for n in range(1, 8)])",
  "answer": "[0.25, 0.5, 1.0, 2.0, 4.0, 5.0, 5.0]",
  "explanation": "Each retry doubles the wait until the cap (5.0) stops it growing. With jitter you'd wait a random time between 0 and each of these values." }
```

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "If the API gateway, the service and the database driver each retry 3 times, a single user request can cause up to 64 attempts against the database.", "answer": true,
  "explanation": "Each layer makes up to 4 attempts (1 + 3 retries), and they multiply: 4 x 4 x 4 = 64. That's why the AWS article recommends retrying at a single point in the stack." }
```

```quiz
{ "id": "q5", "type": "explain", "label": "Design review",
  "prompt": "A Kafka consumer calls a payment provider to capture money for each `order.placed` event. On any exception it retries immediately in a loop until success. Review the design.",
  "model": "Problems: (1) Not idempotent: if the capture succeeded but the response was lost, the retry captures again. Send a stable idempotency key (for example the order id) to the provider, and record the capture in the database keyed by order id. (2) Immediate, unlimited retries hammer a provider that may be overloaded; use capped exponential backoff with jitter and a maximum number of attempts. (3) Retrying on any exception also retries permanent failures (card declined, bad data) forever and blocks the partition; classify errors and send permanent failures to a dead-letter topic or table with an alert. (4) Duplicated events from Kafka need deduplication too, by order id or message id, in the same transaction as recording the capture.",
  "explanation": "Retries need idempotency, limits, backoff and error classification together." }
```

## 6. Your turn: an idempotent payment consumer

You'll make a billing consumer safe against duplicate deliveries, and write the retry helpers its worker uses: a capped exponential backoff with optional jitter, and a `with_retries` wrapper that retries only transient errors. `sleep` and the random source are passed in, so the tests run instantly.

```exercise
ARCH.M03.L03.E1
```
