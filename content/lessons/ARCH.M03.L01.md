---
{
  "id": "ARCH.M03.L01",
  "title": "Off the request path: BackgroundTasks vs a durable queue",
  "difficulty": "intermediate",
  "minutes": 100,
  "prerequisites": ["ARCH.M02", "AS.M02"],
  "objectives": [
    "Identify side effects that don't belong in the request: slow, failure-prone and not needed for the response",
    "Use FastAPI BackgroundTasks correctly: queue after the commit, handle failures inside the task",
    "Predict BackgroundTasks behaviour: after the response, in order, a raising task stops later ones, and nothing survives a restart",
    "Choose between in-process background work and a durable queue from what losing the work would cost"
  ],
  "why": "You picked queue-based fan-out in the assessment, and your adminpanel writes audit logs from a goroutine. Both are 'do it later' decisions. This lesson makes the trade-off explicit: in-process background work is easy and loses work on a crash; a durable queue survives crashes and costs infrastructure and duplicate handling.",
  "applications": [
    "Welcome emails, thumbnails, webhooks, search indexing, analytics events",
    "Keeping p99 latency low when a third-party API is slow",
    "Deciding whether a feature needs Kafka/RabbitMQ or just a background task"
  ],
  "exercises": ["ARCH.M03.L01.E1"],
  "sources": [
    {
      "title": "FastAPI docs: Background Tasks",
      "url": "https://fastapi.tiangolo.com/tutorial/background-tasks/",
      "version": "FastAPI docs (no version on page); behaviour run locally with fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["Background tasks run after returning a response", "A task function can be def or async def", "add_task takes the function plus positional and keyword arguments", "For heavy work that needn't run in the same process, bigger tools like Celery with a queue such as RabbitMQ or Redis can run tasks in multiple processes and servers"]
    },
    {
      "title": "Starlette docs: Background Tasks",
      "url": "https://starlette.dev/background/",
      "version": "Starlette docs (no version on page); installed starlette 1.10.0",
      "verified": "2026-11-12",
      "claims": ["A background task runs only once the response has been sent", "Tasks are executed in order", "If one task raises, the following tasks do not run"]
    },
    {
      "title": "FastAPI docs: Dependencies with yield",
      "url": "https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/",
      "version": "FastAPI docs (no version on page); behaviour run locally with fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["By default the exit code of a dependency with yield runs after the response is sent", "Depends(scope=\"function\") ends the dependency before the response is sent"]
    },
    {
      "title": "Apache Kafka documentation: Message Delivery Semantics",
      "url": "https://kafka.apache.org/44/design/design/",
      "version": "Apache Kafka 4.4 docs",
      "verified": "2026-11-12",
      "claims": ["At least once: messages are never lost but may be redelivered", "Kafka guarantees at-least-once delivery by default"]
    },
    {
      "title": "asyncio: Coroutines and Tasks (create_task)",
      "url": "https://docs.python.org/3.12/library/asyncio-task.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["The event loop keeps only weak references to tasks; save a reference so a task doesn't disappear mid-execution"]
    }
  ]
}
---
## 1. What doesn't belong in the request

A request handler should do what the response depends on, and nothing else. Typical things that sneak in:

- **Slow:** resizing an image, rendering a PDF, calling a third-party API.
- **Failure-prone:** SMTP, webhooks to customer servers. Their outage becomes *your* 500.
- **Not needed for the answer:** the client doesn't need the welcome email to have been sent to know the signup worked.

If a step is all three, move it out. In Go you'd write `go sendWelcome(email)`, and your adminpanel's batched audit writer is a version of that idea. You also know the catch: the goroutine started with `context.Background()` dies with the process, and nobody retries it.

## 2. FastAPI BackgroundTasks

FastAPI's docs: "You can define background tasks to be run *after* returning a response." You declare a `BackgroundTasks` parameter and call `add_task(func, *args, **kwargs)`. The function can be `def` or `async def`.

```python
import time

from fastapi import BackgroundTasks, FastAPI

app = FastAPI()
events = []


def make_thumbnail(photo_id: int) -> None:
    time.sleep(1.0)                                   # stands in for slow image processing
    events.append(f"thumbnail {photo_id} done")


@app.post("/photos/{photo_id}/inline")
def upload_inline(photo_id: int):
    make_thumbnail(photo_id)
    return {"photo_id": photo_id}


@app.post("/photos/{photo_id}/background", status_code=202)
def upload_background(photo_id: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(make_thumbnail, photo_id)
    return {"photo_id": photo_id, "thumbnail": "pending"}
```

Against a real uvicorn server (timed with httpx):

```console
$ python timeit.py
/photos/1/inline       200 {'photo_id': 1} in 1.0s
/photos/2/background   202 {'photo_id': 2, 'thumbnail': 'pending'} in 0.0s
events right after: ['thumbnail 1 done']
events 1.5 s later: ['thumbnail 1 done', 'thumbnail 2 done']
```

The client got its answer immediately, and the thumbnail appeared a second later. `202 Accepted` with `"pending"` tells the client honestly that the work isn't finished yet.

**Testing note:** `TestClient` doesn't return until the background tasks have run, and by default it re-raises an exception from a task in your test. That's convenient for asserting "the email was sent", but it hides the timing. To check that work is *deferred*, call the endpoint function directly with your own `BackgroundTasks()` and look at `tasks.tasks` before running them.

## 3. The rules that bite

Starlette (which FastAPI builds on) documents three: a task "will run only once the response has been sent", "the tasks are executed in order", and "in case one of the tasks raises an exception, the following tasks will not get the opportunity to be executed".

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import warnings\nwarnings.simplefilter(\"ignore\")\nfrom fastapi import BackgroundTasks, FastAPI\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\ndone = []\n\ndef step(name):\n    if name == \"b\":\n        raise RuntimeError(\"b failed\")\n    done.append(name)\n\n@app.post(\"/x\")\ndef x(tasks: BackgroundTasks):\n    for name in \"abc\":\n        tasks.add_task(step, name)\n    return {\"queued\": 3}\n\nr = TestClient(app, raise_server_exceptions=False).post(\"/x\")\nprint(r.status_code, done)",
  "answer": "200 ['a']",
  "explanation": "The response (200) was already sent when the tasks ran. Task b raised, so c never ran, and the client can't know. That's why each task should catch and log its own failures." }
```

The fourth rule is about **ordering with dependencies that commit after `yield`**. On the FastAPI version installed here, run this and look at where the email lands:

```quiz
{ "id": "q2", "type": "output",
  "prompt": "On fastapi 0.162.0, what does this print?",
  "code": "import warnings\nwarnings.simplefilter(\"ignore\")\nfrom typing import Annotated\nfrom fastapi import BackgroundTasks, Depends, FastAPI\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\nlog = []\n\ndef get_session():\n    log.append(\"open\")\n    yield \"session\"\n    log.append(\"commit\")\n\n@app.post(\"/orders\")\ndef create(tasks: BackgroundTasks, s: Annotated[str, Depends(get_session)]):\n    tasks.add_task(log.append, \"send email\")\n    log.append(\"handler\")\n    return {}\n\nTestClient(app).post(\"/orders\")\nprint(log)",
  "answer": "['open', 'handler', 'send email', 'commit']",
  "explanation": "With the default dependency scope, the code after yield (here the commit) ran after the background task. If the commit failed, the customer would already have an email about an order that doesn't exist. Commit in the service before queuing the task, or use scope=\"function\". This ordering has changed between FastAPI versions, so don't rely on it: make the order explicit in your own code." }
```

So the rule from the exercise: **queue the task only after your own code has committed.**

## 4. What you give up

BackgroundTasks runs in the same process, from an in-memory list. That means:

| You lose | Consequence |
|---|---|
| **Durability** | A deploy, crash or OOM kill between the response and the task loses the task. Nobody knows. |
| **Retries** | A failed send is logged (if you log it) and that's it. |
| **Visibility** | No queue length, no "pending" list to inspect. |
| **Scale** | The work competes with requests for the same CPU and workers. |

FastAPI's own docs draw the line: for heavy work that doesn't need the same process, "you might benefit from using other bigger tools like Celery", which use "a message/job queue manager, like RabbitMQ or Redis" and run tasks "in multiple processes, and especially, in multiple servers". For "small background tasks (like sending an email notification)" BackgroundTasks is fine.

The honest question is: **what does it cost if this work is silently lost one time in a thousand?**

- A thumbnail that can be regenerated on the next view: BackgroundTasks.
- A cache warm-up: BackgroundTasks.
- An order confirmation, a payment webhook, an invoice: durable queue or outbox.

`asyncio.create_task` in an async endpoint (AS.M02) is *not* a better BackgroundTasks: FastAPI doesn't track it, and the asyncio docs warn that the event loop keeps only weak references, so you must hold a reference "to avoid a task disappearing mid-execution".

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "Tasks added with BackgroundTasks are retried automatically after a server restart.", "answer": false,
  "explanation": "They live in the process's memory. A restart loses every task that hadn't run yet, and failures are never retried unless you build that." }
```

## 5. Durable queues, briefly

A durable queue moves the work into a separate system that stores it until a **worker process** confirms it's done. **None of these brokers is installed on this machine, so nothing in this section was run.**

- **Kafka** (which your messenger uses): an append-only log that consumers read at their own offsets. Its docs define "at least once" as "messages are never lost but may be redelivered" and state "Kafka guarantees at-least-once delivery by default".
- **RabbitMQ**, and **Celery** or similar task libraries on top of RabbitMQ or Redis: job queues where a worker acknowledges each job. Unacknowledged jobs go back to the queue.

The shape is always the same: the web process *records* the work, and a worker *does* it, retrying on failure. Two problems come with it, and they're the next two lessons:

1. **Recording the work and saving your data must happen together.** If the database commit succeeds and publishing to the broker fails (or the reverse), you've lost or invented an event. That's the outbox (L02).
2. **At-least-once means duplicates.** The worker will sometimes process the same job twice. It must be idempotent (L03).

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "Which side effect most clearly needs a durable queue rather than BackgroundTasks?",
  "options": ["Warming the cache for the page the user just edited", "Logging a debug line about request timing", "Notifying the warehouse system that a paid order must ship", "Regenerating a thumbnail that is rebuilt on demand if missing"], "answer": 2,
  "explanation": "Losing the warehouse notification means a paid order never ships, and nobody notices. The others are cheap to lose or rebuild." }
```

```quiz
{ "id": "q5", "type": "explain", "label": "Design review",
  "prompt": "Your adminpanel writes audit log entries from a goroutine started with `context.Background()`, batching them every few seconds. A colleague ports it to Python as a BackgroundTasks call per request. Is that a faithful port, and is it good enough for an audit log?",
  "model": "Roughly the same guarantees: both are in-process, so a crash or deploy loses whatever is queued (the Go version loses up to one batch; the Python version loses tasks not yet run). The Python version also loses batching, so one write per request. Whether that's acceptable depends on what the audit log is for: if it's compliance or security evidence ('who banned this user'), losing entries is not acceptable. Write the audit row in the same database transaction as the action itself (cheap and exactly consistent), or use an outbox. If it's debugging telemetry, in-process is fine.",
  "explanation": "Pick the mechanism from the cost of losing an entry, not from what's easiest to port." }
```

## 6. Your turn: move the welcome email

The exercise's signup endpoint sends the welcome email inline. Move it into a background task that's queued only after a successful insert and that can't break the signup when SMTP fails.

```exercise
ARCH.M03.L01.E1
```
