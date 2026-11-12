---
{
  "id": "AS.M02.L04",
  "title": "Bounded concurrency: semaphores vs Go worker pools",
  "difficulty": "intermediate",
  "minutes": 90,
  "prerequisites": ["AS.M02.L03"],
  "objectives": [
    "Limit how many coroutines run a section at once with asyncio.Semaphore and async with, and measure the effect of the limit",
    "Map the pattern to Go's buffered-channel semaphore and to a fixed pool of worker goroutines",
    "Build a worker pool with asyncio.Queue, task_done and join, and shut the workers down by cancelling them",
    "Spot the semaphore-per-task bug and other ways a limit silently stops limiting"
  ],
  "why": "Starting 10,000 tasks is easy and cheap for Python; the database, the remote API and your connection pool are the ones that fall over. Every real fan-out needs a limit, and in Go you already reach for a buffered channel or a worker pool without thinking.",
  "applications": [
    "Calling a rate-limited third-party API from many tasks",
    "Keeping concurrent queries below the database connection pool size",
    "Processing a stream of jobs with a fixed number of workers"
  ],
  "exercises": ["AS.M02.L04.E1"],
  "sources": [
    {
      "title": "asyncio: Synchronization Primitives (Semaphore, BoundedSemaphore)",
      "url": "https://docs.python.org/3.12/library/asyncio-sync.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["A semaphore's internal counter is decremented by acquire and incremented by release; when acquire finds it at zero it blocks until another task releases", "The preferred way to use a Semaphore is async with", "BoundedSemaphore raises ValueError in release() if the counter would go above the initial value", "asyncio primitives are not thread-safe"]
    },
    {
      "title": "asyncio: Queues",
      "url": "https://docs.python.org/3.12/library/asyncio-queue.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Queues can distribute workload between several concurrent tasks", "With maxsize > 0, await put() blocks when the queue is full", "join() blocks until every item has been received and processed (task_done called)", "The docs example cancels the workers after join() and gathers them with return_exceptions=True"]
    },
    {
      "title": "Effective Go: Channels (buffered channel as a semaphore)",
      "url": "https://go.dev/doc/effective_go",
      "version": "Effective Go (current; Go installed here: go1.21.0)",
      "verified": "2026-11-12",
      "claims": ["A buffered channel can be used like a semaphore; its capacity limits the number of simultaneous calls", "Alternatively start a fixed number of handler goroutines all reading from the request channel"]
    },
    {
      "title": "Package errgroup (SetLimit)",
      "url": "https://pkg.go.dev/golang.org/x/sync/errgroup",
      "version": "golang.org/x/sync (current docs)",
      "verified": "2026-11-12",
      "claims": ["SetLimit limits the number of active goroutines in the group to at most n"]
    }
  ]
}
---
## 1. Why limit at all

L01 showed 10,000 concurrent tasks finishing in about a second. That's the problem: `gather(*(send_email(u) for u in users))` with 50,000 users opens 50,000 SMTP connections at once. Downstream services rate-limit you, databases run out of connections, and you get a wall of errors that has nothing to do with your code being wrong.

You already solve this in Go in one of two ways (both straight from Effective Go):

```go
sem := make(chan struct{}, 5) // buffered channel as a semaphore: 5 slots
var wg sync.WaitGroup
for i := 0; i < 20; i++ {
	wg.Add(1)
	go func(i int) {
		defer wg.Done()
		sem <- struct{}{}        // acquire: blocks while 5 are in flight
		defer func() { <-sem }() // release
		sendEmail(fmt.Sprintf("user%d", i))
	}(i)
}
wg.Wait()
```

```console
$ go run sem.go        # go1.21.0, sendEmail sleeps 100 ms
limit 5: 0.40s
```

or a fixed number of worker goroutines reading from one channel. asyncio has a direct equivalent of each.

## 2. `asyncio.Semaphore`

A semaphore holds a counter of permits. `acquire` takes one and **waits when there are none left**; `release` gives one back. The docs' preferred form is `async with`, which releases even on errors and cancellation. Measured on this machine, 20 emails of 100 ms each:

```python
import asyncio, time

in_flight = peak = 0

async def send_email(to):
    global in_flight, peak
    in_flight += 1
    peak = max(peak, in_flight)
    await asyncio.sleep(0.1)            # SMTP round trip
    in_flight -= 1
    return f"sent to {to}"

async def send_limited(gate, to):
    async with gate:                    # at most N holders at a time
        return await send_email(to)

async def main(limit):
    global peak
    peak = 0
    gate = asyncio.Semaphore(limit)
    t = time.perf_counter()
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(send_limited(gate, f"user{i}")) for i in range(20)]
    print(f"limit {limit:2}: peak {peak:2}, {time.perf_counter() - t:.2f}s, first: {tasks[0].result()}")

for limit in (1, 5, 20):
    asyncio.run(main(limit))
```

```console
limit  1: peak  1, 2.01s, first: sent to user0
limit  5: peak  5, 0.40s, first: sent to user0
limit 20: peak 20, 0.10s, first: sent to user0
```

Exactly the Go numbers for limit 5 (0.40 s = 4 waves of 100 ms). All 20 tasks exist from the start; 15 of them simply wait at `async with gate` for a permit.

Notice the `in_flight += 1` counter: in Go you'd need `atomic.AddInt64` or a mutex for it. Here there's no `await` between reading and writing it, so (AS.M01.L02) no other task can interleave.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nin_flight = peak = 0\n\nasync def call(gate):\n    global in_flight, peak\n    async with gate:\n        in_flight += 1\n        peak = max(peak, in_flight)\n        await asyncio.sleep(0.01)\n        in_flight -= 1\n\nasync def main():\n    gate = asyncio.Semaphore(2)\n    async with asyncio.TaskGroup() as tg:\n        for _ in range(5):\n            tg.create_task(call(gate))\n    print(peak)\n\nasyncio.run(main())",
  "answer": "2",
  "explanation": "Five tasks share one semaphore with 2 permits, so at most two are inside the async with block at any moment." }
```

```quiz
{ "id": "q2", "type": "output", "label": "Debugging",
  "prompt": "Someone \"simplified\" the code. What does this print now?",
  "code": "import asyncio\n\nin_flight = peak = 0\n\nasync def call():\n    global in_flight, peak\n    async with asyncio.Semaphore(2):\n        in_flight += 1\n        peak = max(peak, in_flight)\n        await asyncio.sleep(0.01)\n        in_flight -= 1\n\nasync def main():\n    async with asyncio.TaskGroup() as tg:\n        for _ in range(5):\n            tg.create_task(call())\n    print(peak)\n\nasyncio.run(main())",
  "answer": "5",
  "explanation": "Each call creates its own semaphore with 2 permits, so nobody ever waits: no limit at all. All tasks must share one semaphore object." }
```

## 3. Worker pool with `asyncio.Queue`

The other Go pattern: N workers, one queue of jobs. `asyncio.Queue` is built for this. Workers loop on `await queue.get()`, call `queue.task_done()` per item, and `await queue.join()` waits until every item has been processed. Then you cancel the workers, which are stuck waiting for more work (the same shutdown the docs' example uses):

```python
import asyncio, time

async def worker(name, queue, done):
    while True:
        to = await queue.get()
        await asyncio.sleep(0.1)          # SMTP round trip
        done.append((name, to))
        queue.task_done()

async def main():
    queue = asyncio.Queue()
    for i in range(20):
        queue.put_nowait(f"user{i}")
    done = []
    t = time.perf_counter()
    workers = [asyncio.create_task(worker(f"w{n}", queue, done)) for n in range(5)]
    await queue.join()                    # every item got task_done()
    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)
    print(f"{len(done)} emails by {len({w for w, _ in done})} workers in {time.perf_counter() - t:.2f}s")

asyncio.run(main())
```

```console
20 emails by 5 workers in 0.40s
```

Same 0.40 s. With `asyncio.Queue(maxsize=100)`, `await queue.put(...)` blocks when the queue is full, which is backpressure for a producer that's faster than the workers, like a buffered Go channel.

Which one to choose?

| Semaphore | Worker pool (Queue) |
|---|---|
| You have a list of jobs now | Jobs arrive over time (a stream, a consumer loop) |
| One task per job, few lines of code | N long-lived tasks; can hold one connection each |
| Results map back to inputs easily | You collect results yourself |

`errgroup` with `SetLimit(n)` in Go is the TaskGroup-plus-semaphore combination in one type.

```quiz
{ "id": "q3", "type": "choice", "label": "Application",
  "prompt": "A service consumes events from a Kafka-like stream forever and must process at most 8 at a time, each worker reusing one DB connection. Which design fits best?",
  "options": ["One gather() over all events", "A TaskGroup with one task per event and no limit", "8 worker tasks reading from an asyncio.Queue fed by the consumer", "asyncio.to_thread for each event"], "answer": 2,
  "explanation": "Jobs arrive over time and each worker keeps a resource for its lifetime: that's a worker pool. A bounded Queue also gives backpressure to the consumer." }
```

## 4. Limits that silently stop limiting

- **A semaphore per task** (q2): every task gets fresh permits. Create the semaphore once and share it.
- **Manual `acquire()` without `release()` on every path.** An exception between them leaks a permit, and after `limit` errors everything hangs. Use `async with`. `BoundedSemaphore` additionally raises `ValueError` if you release more than you acquired.
- **Using it across threads.** asyncio primitives are not thread-safe; use `threading.Semaphore` for threads.
- **A limit with no timeout.** A permit holder that hangs holds its permit forever. Combine with L03: `async with gate:` and inside it `async with asyncio.timeout(...)`.

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "`asyncio.Semaphore` can safely limit how many OS threads (for example `asyncio.to_thread` workers) enter a section at once, when acquired from inside those threads.", "answer": false,
  "explanation": "asyncio primitives are not thread-safe and are meant for tasks on one event loop. Inside threads, use threading.Semaphore. (Acquiring an asyncio.Semaphore in the coroutine *before* calling to_thread is fine.)" }
```

```quiz
{ "id": "q5", "type": "explain", "label": "Application",
  "prompt": "A nightly job calls a partner API for 30,000 customers with gather() and gets thousands of HTTP 429 (Too Many Requests) errors. The partner allows 20 concurrent requests. What do you change, and what Go code would you have written for the same job?",
  "model": "Share one asyncio.Semaphore(20) and wrap each request in `async with sem:` (or run 20 workers from an asyncio.Queue), with a timeout inside so a hung request can't hold a permit forever. In Go: a buffered channel of capacity 20 used as a semaphore (or errgroup with SetLimit(20)), or 20 worker goroutines reading from a jobs channel.",
  "explanation": "Concurrency is cheap; the downstream limit is what you design for." }
```

## 5. Your turn

Write `fetch_many`: fetch a list of URLs concurrently with at most `limit` in flight and results in input order. The fake site in the tests records the peak number of concurrent requests and checks you use the limit fully, not just stay under it.

```exercise
AS.M02.L04.E1
```
