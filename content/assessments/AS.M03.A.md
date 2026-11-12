---
{ "id": "AS.M03.A", "module": "AS.M03", "title": "AS.M03 module assessment: async FastAPI and async DB", "minutes": 15 }
---
Answer without the lessons open and without AI, and don't run the code first. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before moving on.

```quiz
{ "id": "a1", "type": "output", "label": "Predict the order",
  "prompt": "Two requests are sent concurrently. What does this print?",
  "code": "import asyncio, time\nimport httpx\nfrom fastapi import FastAPI\n\napp = FastAPI()\nlog = []\n\n@app.get(\"/job/{n}\")\nasync def job(n: int):\n    log.append(f\"start {n}\")\n    time.sleep(0.05)\n    log.append(f\"end {n}\")\n    return {\"n\": n}\n\nasync def main():\n    transport = httpx.ASGITransport(app=app)\n    async with httpx.AsyncClient(transport=transport, base_url=\"http://test\") as client:\n        await asyncio.gather(client.get(\"/job/1\"), client.get(\"/job/2\"))\n    print(log)\n\nasyncio.run(main())",
  "answer": "['start 1', 'end 1', 'start 2', 'end 2']",
  "explanation": "The endpoint is async def, so it runs on the event loop, and time.sleep blocks that loop. The second request can't start until the first has finished: the requests are served one after the other." }
```

```quiz
{ "id": "a2", "type": "choice",
  "prompt": "In the code above, `async def job` is changed to plain `def job` and nothing else. What happens to the two concurrent requests?",
  "options": ["Still one after the other", "Both run at the same time, in threadpool worker threads", "FastAPI raises an error because def endpoints can't sleep", "They run in two separate event loops"], "answer": 1,
  "explanation": "FastAPI runs def path operations in an external threadpool, so each blocking sleep occupies one worker thread and the event loop stays free to start the other request." }
```

```quiz
{ "id": "a3", "type": "truefalse",
  "prompt": "A dependency declared with plain `def` (for example one that opens a sync DB connection) is run on the event loop's thread.", "answer": false,
  "explanation": "The FastAPI docs: a def dependency is run in the external threadpool, like a def endpoint. async def dependencies run on the loop." }
```

```quiz
{ "id": "a4", "type": "choice", "label": "Debugging",
  "prompt": "`async def get_conn(): conn = await aiosqlite.connect(DB); try: yield conn; await conn.commit()` / `except Exception: await conn.rollback()` / `finally: await conn.close()`. An endpoint using it raises ValueError. What's wrong with this dependency?",
  "options": ["Nothing", "The rollback is in the wrong place", "The except block doesn't re-raise, so the error is swallowed and the server has no log of it", "close() must come before rollback()"], "answer": 2,
  "explanation": "After rolling back, the dependency must re-raise. The FastAPI docs warn that otherwise the client gets a 500 and the server has no record of the error." }
```

```quiz
{ "id": "a5", "type": "choice", "label": "Application",
  "prompt": "Which async test proves that POST /orders really committed the order?",
  "options": ["Assert the POST returned 201", "After the POST, open a new aiosqlite connection to the test DB file and SELECT the order", "Run the test against \":memory:\" so it's fast", "Assert the endpoint returned the order's id"], "answer": 1,
  "explanation": "Another connection only sees committed data. The status code and response body are produced before (or regardless of) the commit; ':memory:' gives every connection a different empty database." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "Review this endpoint and say what you'd change: `@app.get(\"/report\") async def report(session: SessionDep): users = sync_crm_client.list_users(); rows = await asyncio.gather(*(session.execute(q) for q in queries)); return build(users, rows)` (SessionDep yields one AsyncSession per request).",
  "model": "1) sync_crm_client.list_users() blocks the event loop inside async def: wrap it in await asyncio.to_thread(...) (or use an async client). 2) The gather runs several queries concurrently on one AsyncSession, which the SQLAlchemy docs say is not safe for concurrent tasks: run them sequentially, or give each its own session. 3) Make sure the session dependency commits/rolls back and re-raises, ideally with scope=\"function\" so the commit happens before the response.",
  "explanation": "Blocking call in async def; one AsyncSession shared by concurrent tasks." }
```
