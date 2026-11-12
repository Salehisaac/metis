---
{
  "id": "AS.M01.L02",
  "title": "One thread, cooperative scheduling: asyncio vs goroutines",
  "difficulty": "intermediate",
  "minutes": 100,
  "prerequisites": ["AS.M01.L01"],
  "objectives": [
    "Contrast goroutines (preemptively scheduled by the Go runtime across OS threads) with asyncio tasks (cooperatively scheduled on one thread by the event loop)",
    "Predict the output order and the total time when a coroutine uses time.sleep instead of await asyncio.sleep",
    "Explain why CPU-bound code with no await stalls every other task, and break it up with await asyncio.sleep(0)",
    "Identify which shared-state updates are safe between tasks (no await in between) and which race (an await between read and write)"
  ],
  "why": "Your Go intuition says 'the runtime will schedule around a slow goroutine'. In asyncio nobody schedules around you: one blocking call or long loop freezes every request on the server. Knowing exactly where switches can happen also tells you where races can and can't happen.",
  "applications": [
    "Recognising time.sleep, sync HTTP clients and heavy loops inside async def as 'blocks the whole server'",
    "Keeping latency low for every client of an async API, not just the slow one",
    "Reasoning about shared state in async code without reaching for a mutex everywhere"
  ],
  "exercises": ["AS.M01.L02.E1"],
  "sources": [
    {
      "title": "Developing with asyncio (concurrency and multithreading; blocking code)",
      "url": "https://docs.python.org/3.12/library/asyncio-dev.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["An event loop runs in a thread and executes all callbacks and Tasks in its thread", "While a Task is running in the event loop, no other Tasks can run in the same thread", "Blocking (CPU-bound) code should not be called directly: a 1-second CPU-intensive calculation delays all concurrent Tasks and IO by 1 second"]
    },
    {
      "title": "asyncio: Coroutines and Tasks (sleep)",
      "url": "https://docs.python.org/3.12/library/asyncio-task.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["sleep() always suspends the current task, allowing other tasks to run", "sleep(0) is an optimized path to let other tasks run; long-running functions can use it to avoid blocking the event loop"]
    },
    {
      "title": "Go 1.14 Release Notes (Runtime)",
      "url": "https://go.dev/doc/go1.14",
      "version": "Go 1.14",
      "verified": "2026-11-12",
      "claims": ["Goroutines are asynchronously preemptible", "Loops without function calls no longer potentially deadlock the scheduler"]
    },
    {
      "title": "Package runtime (GOMAXPROCS)",
      "url": "https://pkg.go.dev/runtime",
      "version": "Go standard library (current docs)",
      "verified": "2026-11-12",
      "claims": ["GOMAXPROCS limits the number of OS threads that can execute user-level Go code simultaneously", "The default is derived from the number of logical CPUs unless the GOMAXPROCS environment variable is set"]
    },
    {
      "title": "asyncio: Synchronization Primitives (Lock)",
      "url": "https://docs.python.org/3.12/library/asyncio-sync.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["asyncio.Lock is a mutex for asyncio tasks; the preferred way to use it is async with", "asyncio primitives are not thread-safe"]
    }
  ]
}
---
## 1. Two schedulers

**Go.** A goroutine is scheduled by the Go runtime onto OS threads. `GOMAXPROCS` threads (by default about one per CPU) run Go code *at the same time*. And since Go 1.14, goroutines are **asynchronously preemptible**: the runtime can pause a goroutine in the middle of a tight loop and run another. You never have to "let others run".

**asyncio.** The event loop runs on **one thread** and runs **one task at a time**. A task keeps the thread until it **suspends at an `await`** on something that actually waits (a sleep, a socket read, another task). The loop never interrupts it. This is *cooperative* scheduling: each task must give control back. The asyncio docs: while a Task is running in the event loop, no other Tasks can run in the same thread.

| | Go goroutines | asyncio tasks |
|---|---|---|
| Who switches | the runtime, any time (preemptive) | the task itself, only at `await` (cooperative) |
| Threads | up to `GOMAXPROCS` running Go code in parallel | one: the event loop's thread |
| Blocking call (`time.Sleep`, sync I/O) | parks that goroutine; others keep running | `time.sleep` freezes **everything** |
| Long CPU loop | preempted; others keep running | nothing else runs until it ends |

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "A task is in a loop that does arithmetic and never awaits. What can interrupt it so another task on the same event loop runs?",
  "options": ["The event loop, after a time slice", "Nothing: the other tasks wait until it awaits or finishes", "Any await in another task", "The OS thread scheduler, which runs the other task on a second thread"], "answer": 1,
  "explanation": "asyncio is cooperative. The loop only regains control when the running task suspends. Go's runtime would preempt the loop; asyncio never does." }
```

## 2. `time.sleep` vs `await asyncio.sleep`

Same two tasks, two kinds of sleep. Measured on this machine:

```python
import asyncio, time

async def polite(name):
    print("start", name)
    await asyncio.sleep(1)      # suspends: the loop runs others
    print("end", name)

async def rude(name):
    print("start", name)
    time.sleep(1)               # blocks the whole thread, loop included
    print("end", name)

async def run_pair(worker):
    t = time.perf_counter()
    a = asyncio.create_task(worker("a"))
    b = asyncio.create_task(worker("b"))
    await a
    await b
    print(f"{worker.__name__}: {time.perf_counter() - t:.2f}s")

asyncio.run(run_pair(polite))
asyncio.run(run_pair(rude))
```

```console
start a
start b
end a
end b
polite: 1.00s
start a
end a
start b
end b
rude: 2.00s
```

`rude` is inside `async def`, and it's even run as a task, but `time.sleep` doesn't know about the event loop: it puts the **thread** to sleep, and the loop lives on that thread. `async def` doesn't make code non-blocking; only awaiting something that suspends does.

In a web server, "the thread" is every request in flight. One `time.sleep(1)` (or `requests.get`, or a sync DB driver) inside an async endpoint stalls **all** clients for that second. AS.M03 shows this in FastAPI.

```quiz
{ "id": "q2", "type": "output", "label": "Predict the order",
  "prompt": "What does this print?",
  "code": "import asyncio, time\n\nasync def worker(name):\n    print(\"start\", name)\n    time.sleep(0.05)\n    print(\"end\", name)\n\nasync def main():\n    a = asyncio.create_task(worker(\"a\"))\n    b = asyncio.create_task(worker(\"b\"))\n    await a\n    await b\n\nasyncio.run(main())",
  "answer": "start a\nend a\nstart b\nend b",
  "explanation": "time.sleep never suspends the task, so worker a runs from start to end before the loop can start b. With await asyncio.sleep(0.05) you'd get start a, start b, end a, end b." }
```

## 3. CPU work blocks too

It isn't only sleeps. Any stretch of code without an `await` is one uninterrupted step. Here a heartbeat task should tick every 0.2 s, and the main coroutine does 1 s of pure arithmetic in between:

```python
import asyncio, time

async def heartbeat(start):
    while True:
        print(f"  tick at {time.perf_counter() - start:.1f}s")
        await asyncio.sleep(0.2)

def crunch(n):
    return sum(i * i for i in range(n))

async def main():
    start = time.perf_counter()
    hb = asyncio.create_task(heartbeat(start))
    await asyncio.sleep(0.5)
    print(f"crunch starts at {time.perf_counter() - start:.1f}s")
    crunch(50_000_000)          # pure CPU: no await inside
    print(f"crunch ends at {time.perf_counter() - start:.1f}s")
    await asyncio.sleep(0.5)
    hb.cancel()

asyncio.run(main())
```

```console
  tick at 0.0s
  tick at 0.2s
  tick at 0.4s
crunch starts at 0.5s
crunch ends at 1.7s
  tick at 1.7s
  tick at 1.9s
  tick at 2.1s
```

No ticks between 0.4 s and 1.7 s. The heartbeat wasn't slow; it never got the thread. The asyncio docs give the same example: a CPU-intensive calculation of 1 second delays all concurrent tasks and I/O by 1 second.

Two fixes, depending on the size of the work:

- **Yield now and then.** Inside a long loop, `await asyncio.sleep(0)` every N iterations. The docs describe `sleep(0)` as the optimized way to let other tasks run, meant for exactly this. The work still uses the loop's thread, but others get turns.
- **Move it off the loop's thread.** L03: `asyncio.to_thread` and process pools.

```quiz
{ "id": "q3", "type": "output", "label": "Predict the order",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nasync def ticker():\n    for i in range(3):\n        print(\"tick\", i)\n        await asyncio.sleep(0)\n\nasync def main():\n    t = asyncio.create_task(ticker())\n    total = sum(range(1_000_000))\n    print(\"sum done\")\n    await t\n\nasyncio.run(main())",
  "answer": "sum done\ntick 0\ntick 1\ntick 2",
  "explanation": "The ticker task is scheduled but can't start until main suspends. main computes the sum and prints without awaiting, so 'sum done' comes first. Only at `await t` does the ticker get the thread." }
```

## 4. The upside: no switch, no race

Cooperative scheduling has one big benefit. Between two `await`s, your task runs alone, so **code without an `await` in it can't be interleaved with other tasks**. In Go, `balance -= amount` from two goroutines is a data race and needs a mutex. In asyncio it's safe, *as long as there's no `await` between the read and the write*:

```python
import asyncio

balance = 100

async def withdraw_safe(amount):
    global balance
    if balance >= amount:          # no await between check and update:
        balance -= amount          # no other task can run in between

async def withdraw_racy(amount):
    global balance
    if balance >= amount:
        await asyncio.sleep(0)     # e.g. an audit-log call: other tasks run here
        balance -= amount

async def main(worker):
    global balance
    balance = 100
    t1 = asyncio.create_task(worker(80))
    t2 = asyncio.create_task(worker(80))
    await t1
    await t2
    print(worker.__name__, balance)

asyncio.run(main(withdraw_safe))
asyncio.run(main(withdraw_racy))
```

```console
withdraw_safe 20
withdraw_racy -60
```

The racy one is a classic check-then-act bug: both tasks saw 100, both passed the check, then both withdrew. Every `await` is a point where the world can change under you. When a read and a write must span an `await`, protect them with `asyncio.Lock` (`async with lock:`). It's a mutex for tasks, not for threads: the docs say asyncio primitives are not thread-safe.

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "Two asyncio tasks on the same loop each run `hits[path] += 1` (no await on that line). One of the increments can be lost because the other task interrupts in the middle.", "answer": false,
  "explanation": "A task only gives up the thread at an await. There's none inside that statement, so it can't be interleaved with another task. (Threads would be a different story.)" }
```

```quiz
{ "id": "q5", "type": "output", "label": "Debugging",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nseats = 10\n\nasync def book():\n    global seats\n    left = seats\n    await asyncio.sleep(0)   # e.g. write an audit record\n    seats = left - 1\n\nasync def main():\n    a = asyncio.create_task(book())\n    b = asyncio.create_task(book())\n    await a\n    await b\n    print(seats)\n\nasyncio.run(main())",
  "answer": "9",
  "explanation": "Both tasks read 10 before either writes, because each suspends between the read and the write. Both then write 9: a lost update. Read and write without an await in between, or hold an asyncio.Lock across them." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "In a Go service you'd happily call a slow sync function inside a goroutine. Why is the same call inside an `async def` FastAPI endpoint a problem, and what single fact about asyncio explains it?",
  "model": "asyncio runs all tasks on the event loop's one thread and never preempts them. A slow sync call holds that thread, so no other request can make progress until it returns. Go's runtime would park the goroutine (or preempt it) and keep running others on other threads.",
  "explanation": "One thread plus cooperative switching means a blocking call blocks everyone." }
```

## 5. Your turn

The exercise gives you two async functions that hog the loop: one waits with `time.sleep`, the other is a long loop with no `await`. Make both cooperate, without threads. The tests run a second task next to yours and check that it got turns.

```exercise
AS.M01.L02.E1
```
