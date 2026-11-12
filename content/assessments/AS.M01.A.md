---
{ "id": "AS.M01.A", "module": "AS.M01", "title": "AS.M01 module assessment: event loop and coroutines vs goroutines", "minutes": 15 }
---
Answer without the lessons open and without AI, and don't run the code first. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before AS.M02.

```quiz
{ "id": "a1", "type": "output", "label": "Predict the order",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nasync def fetch(n):\n    print(\"fetch\", n)\n    await asyncio.sleep(0)\n    return n * 10\n\nasync def main():\n    a = await fetch(1)\n    print(\"got\", a)\n    b = await fetch(2)\n    print(\"got\", b)\n\nasyncio.run(main())",
  "answer": "fetch 1\ngot 10\nfetch 2\ngot 20",
  "explanation": "Each await waits for fetch to finish before main continues. Nothing runs in the background, so the calls happen strictly in order." }
```

```quiz
{ "id": "a2", "type": "truefalse",
  "prompt": "`await load()` runs the coroutine `load()` in a new thread so that the caller can continue meanwhile.", "answer": false,
  "explanation": "await starts no thread, and the caller doesn't continue: it is suspended until load() has a result. Everything runs on the event loop's one thread." }
```

```quiz
{ "id": "a3", "type": "output", "label": "Predict the order",
  "prompt": "What does this print?",
  "code": "import asyncio, time\n\nasync def polite():\n    print(\"polite start\")\n    await asyncio.sleep(0.05)\n    print(\"polite end\")\n\nasync def rude():\n    print(\"rude start\")\n    time.sleep(0.2)\n    print(\"rude end\")\n\nasync def main():\n    p = asyncio.create_task(polite())\n    r = asyncio.create_task(rude())\n    await p\n    await r\n\nasyncio.run(main())",
  "answer": "polite start\nrude start\nrude end\npolite end",
  "explanation": "polite suspends at asyncio.sleep, so rude starts. rude's time.sleep blocks the thread for 0.2 s without ever suspending, so polite can't resume (even though its 0.05 s are over) until rude has finished." }
```

```quiz
{ "id": "a4", "type": "choice", "label": "Debugging",
  "prompt": "`is_banned` is `async def`. A handler does `if is_banned(user_id): return 403`. What happens?",
  "options": ["Every user gets 403, and Python warns that is_banned was never awaited", "It works, just slower", "SyntaxError: is_banned must be awaited", "is_banned runs in a background thread and the check uses its result"], "answer": 0,
  "explanation": "Without await, is_banned(user_id) is a coroutine object. Objects are truthy, so the branch is always taken, and the coroutine never runs (RuntimeWarning: never awaited)." }
```

```quiz
{ "id": "a5", "type": "choice",
  "prompt": "Inside an async endpoint you must call `ftp.download(path)` from a sync-only library; it mostly waits on the network. What should you write?",
  "options": ["data = ftp.download(path)", "data = await asyncio.to_thread(ftp.download, path)", "data = await asyncio.to_thread(ftp.download(path))", "data = await asyncio.sleep(0) or ftp.download(path)"], "answer": 1,
  "explanation": "to_thread runs the blocking call in a worker thread while the loop serves others. Option 3 calls download immediately on the loop's thread and passes its result to to_thread." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "Explain to a Go developer, in three or four sentences, why a CPU-heavy loop in one goroutine doesn't hurt other goroutines, but the same loop in one asyncio task stalls every other task. Include what you'd do about it in Python.",
  "model": "Go's runtime schedules goroutines preemptively across up to GOMAXPROCS OS threads, so a busy goroutine is paused or runs in parallel while others continue. asyncio runs all tasks on one thread and only switches when the running task awaits something that suspends; a loop with no await keeps the thread until it ends. In Python, yield inside the loop with await asyncio.sleep(0) every N iterations, or move the work off the loop's thread: a process pool via run_in_executor for real CPU work (threads don't add CPU because of the GIL).",
  "explanation": "Preemptive and parallel vs cooperative on one thread." }
```
