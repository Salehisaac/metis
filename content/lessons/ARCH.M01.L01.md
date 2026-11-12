---
{
  "id": "ARCH.M01.L01",
  "title": "API, service and repository layers",
  "difficulty": "intermediate",
  "minutes": 100,
  "prerequisites": ["WEB.M05"],
  "objectives": [
    "Say what belongs in the API, service and repository layer of a FastAPI app, and put a given line of code in the right one",
    "Keep dependencies pointing one way (API to service to repository) and explain what breaks when they don't",
    "Raise domain exceptions in the service and map them to status codes in one place in the API layer",
    "Refactor a working 'fat' endpoint into three layers without changing its HTTP behaviour"
  ],
  "why": "You've worked inside a layered Go codebase (handlers, logic, DAO) that someone else designed, and your adminpanel even documents a layering rule. Designing a system yourself starts with deciding these boundaries on purpose: what each layer may know, and which way the imports point. Get this right and the rest of the module (transactions, fakes) has somewhere to live.",
  "applications": [
    "Testing business rules with a function call instead of an HTTP request",
    "Reusing one service from an endpoint, a CLI command and a queue worker",
    "Swapping raw SQL for SQLAlchemy (or adding a cache) by changing one layer"
  ],
  "exercises": ["ARCH.M01.L01.E1"],
  "sources": [
    {
      "title": "Patterns of Enterprise Application Architecture catalog: Service Layer",
      "url": "https://martinfowler.com/eaaCatalog/serviceLayer.html",
      "version": "Martin Fowler, PoEAA online catalog (undated page)",
      "verified": "2026-11-12",
      "claims": ["A service layer defines an application's boundary and its set of available operations", "It coordinates the application's response in each operation, including controlling transactions"]
    },
    {
      "title": "Patterns of Enterprise Application Architecture catalog: Repository",
      "url": "https://martinfowler.com/eaaCatalog/repository.html",
      "version": "Martin Fowler, PoEAA online catalog (undated page)",
      "verified": "2026-11-12",
      "claims": ["A repository mediates between the domain and data mapping layers using a collection-like interface"]
    },
    {
      "title": "FastAPI docs: Bigger Applications - Multiple Files",
      "url": "https://fastapi.tiangolo.com/tutorial/bigger-applications/",
      "version": "FastAPI docs (no version on page); behaviour run locally with fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["APIRouter is like a mini FastAPI class for splitting path operations into modules", "app.include_router adds a router's routes to the main app"]
    },
    {
      "title": "FastAPI docs: Dependencies",
      "url": "https://fastapi.tiangolo.com/tutorial/dependencies/",
      "version": "FastAPI docs (no version on page); behaviour run locally with fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["Depends takes a callable that FastAPI calls to provide what a path operation needs", "Dependencies are meant for shared logic, database connections and security"]
    }
  ]
}
---
## 1. The fat endpoint

Here's how most first FastAPI apps look. One function does everything:

```python
@app.post("/items/{sku}/take")
def take(sku: str, body: TakeIn, conn=Depends(get_conn)):
    row = conn.execute("SELECT on_hand FROM items WHERE sku = ?", (sku.upper(),)).fetchone()
    if row is None:
        raise HTTPException(404, "unknown item")
    if row[0] < body.qty:
        raise HTTPException(409, "not enough stock")
    conn.execute("UPDATE items SET on_hand = ? WHERE sku = ?", (row[0] - body.qty, sku.upper()))
    return {"sku": sku.upper(), "on_hand": row[0] - body.qty}
```

It works. The problems show up later:

- **You can't test the rule "you can't take more than is on hand" without HTTP.** Every test needs a TestClient and a database.
- **You can't reuse it.** A nightly job or a queue worker that also takes stock must copy the logic, and the two copies drift apart.
- **Everything changes together.** Renaming a column, changing a status code and changing a rule all touch the same function.

In your Go work you've seen the cure: go-zero projects split code into a handler, a logic layer and a model/DAO layer, and your adminpanel's `dao.go` documents which layer may call what. Python has no framework that forces this. You decide it.

## 2. Three layers, three questions

| Layer | Answers | Owns | Must not know about |
|---|---|---|---|
| **API** (routers, endpoints) | What does HTTP see? | Parsing and validation (Pydantic), status codes, auth dependencies, response shape | SQL |
| **Service** | Is this allowed, and what happens? | Business rules, orchestration of several repositories, the transaction boundary (next lesson) | HTTP, FastAPI, SQL |
| **Repository** | How is it stored? | SQL or ORM queries, mapping rows to plain values | Business rules, HTTP |

Martin Fowler's catalog describes the same split. A **service layer** "defines an application's boundary" with "a set of available operations" and coordinates the response in each one. A **repository** "mediates between the domain and data mapping layers using a collection-like interface". You don't need the book. The table above is the working version.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "A rule says 'a customer can't have more than 3 open orders'. Where does the check belong?",
  "options": ["In the endpoint, before calling the service", "In the service", "In the repository's insert method", "In a Pydantic validator on the request body"], "answer": 1,
  "explanation": "It's a business rule, so it lives in the service. The endpoint would make it HTTP-only (a worker could bypass it). The repository would mix rules into storage. Pydantic validates the shape of one request, and it can't count orders in the database." }
```

## 3. Dependencies point down

The import rule is what makes layers real: **API imports service, service imports repository, never the other way.** Here is the stock example split up. It runs as three files plus a test client.

```python
# stock_repo.py: SQL lives here and nowhere else
class StockRepo:
    def __init__(self, conn):
        self.conn = conn

    def get_item(self, sku: str) -> dict | None:
        row = self.conn.execute("SELECT sku, on_hand FROM items WHERE sku = ?", (sku,)).fetchone()
        return None if row is None else {"sku": row[0], "on_hand": row[1]}

    def set_on_hand(self, sku: str, on_hand: int) -> None:
        self.conn.execute("UPDATE items SET on_hand = ? WHERE sku = ?", (on_hand, sku))
```

```python
# stock_service.py: rules only, no SQL, no HTTP
class StockError(Exception): ...
class UnknownItem(StockError): ...
class NotEnoughStock(StockError): ...


def take_stock(repo, sku: str, qty: int) -> int:
    if qty <= 0:
        raise ValueError("qty must be positive")
    item = repo.get_item(sku.strip().upper())
    if item is None:
        raise UnknownItem(sku)
    if item["on_hand"] < qty:
        raise NotEnoughStock(sku)
    left = item["on_hand"] - qty
    repo.set_on_hand(item["sku"], left)
    return left
```

```python
# stock_api.py: HTTP only
@app.post("/items/{sku}/take")
def take(sku: str, body: TakeIn, repo: Annotated[StockRepo, Depends(get_repo)]):
    try:
        left = stock_service.take_stock(repo, sku, body.qty)
    except stock_service.UnknownItem:
        raise HTTPException(404, "unknown item")
    except stock_service.NotEnoughStock:
        raise HTTPException(409, "not enough stock")
    return {"sku": sku.upper(), "on_hand": left}
```

`get_repo` is a dependency with `yield` (WEB.M05): it opens `with conn:` around the request and yields `StockRepo(conn)`. Four requests through TestClient, with 5 bolts in stock:

```console
$ python run_api.py
200 {'sku': 'BOLT-8', 'on_hand': 2}
409 {'detail': 'not enough stock'}
404 {'detail': 'unknown item'}
422 validation error
```

The payoff: the rule runs without FastAPI at all. A dict-backed stand-in for the repository is enough (L03 makes this a proper fake):

```console
$ python svc_test.py            # take_stock(fake_repo, " bolt-8 ", 2), then 1 more
0
NotEnoughStock BOLT-8
```

**Why not raise `HTTPException` in the service?** Because then the service imports FastAPI, and the dependency points *up*. A queue worker calling `take_stock` would get an HTTP 409 object, which means nothing to it. In Go terms: your logic package would import `net/http` just to report "not enough stock".

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "It's fine for the repository to raise `HTTPException(404)` when a row is missing, because the endpoint would return 404 anyway.", "answer": false,
  "explanation": "That makes the storage layer depend on the web framework, and it decides an HTTP response two layers away from HTTP. Return None (or raise a domain exception) and let the API layer choose the status code." }
```

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "Which import breaks the dependency direction?",
  "options": ["`stock_api.py`: `import stock_service`", "`stock_service.py`: `from stock_repo import StockRepo`", "`stock_repo.py`: `from stock_service import NotEnoughStock`", "`stock_api.py`: `from stock_repo import StockRepo`"], "answer": 2,
  "explanation": "The repository importing from the service points upward, and it usually ends in a circular import. The API importing the repository type is allowed (it builds one to pass in), though some teams let only the service touch it." }
```

## 4. One place for the error mapping

With several domain errors, a chain of `except` clauses in every endpoint gets repetitive. Give the errors a common base class, catch the base once, and look up the status code. Python's exception classes form a hierarchy, so a lookup can walk it:

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "class DomainError(Exception): pass\nclass NotFound(DomainError): pass\nclass Conflict(DomainError): pass\nclass OutOfStock(Conflict): pass\n\nSTATUS = {NotFound: 404, Conflict: 409}\n\ndef to_status(exc):\n    for cls in type(exc).__mro__:\n        if cls in STATUS:\n            return STATUS[cls]\n    return 500\n\nprint(to_status(OutOfStock()), to_status(KeyError()))",
  "answer": "409 500",
  "explanation": "`__mro__` lists a class and then its bases in order: OutOfStock, Conflict, DomainError, Exception, ... The first one in the table is Conflict, so 409. KeyError isn't a domain error at all, so it falls through to 500. That's what you want: a bug should look like a bug, not like a 404." }
```

**Common mistakes:**

- `except Exception: raise HTTPException(400)`. Every bug becomes a "bad request", and the client is blamed for your `KeyError`. Catch your domain base class only.
- Returning `None` from the service to mean "not found" *and* "not allowed". The endpoint can't tell them apart. Use distinct exceptions.
- Mapping errors in some endpoints and not others. One table (or FastAPI exception handlers, once several routers share errors) keeps it consistent.

## 5. Where FastAPI's own tools fit

- **`APIRouter`** splits the API layer into modules. FastAPI's docs call it a "mini `FastAPI`" class, which you add to the app with `app.include_router(...)`. That's file organisation *within* the API layer. It doesn't create a service layer by itself.
- **`Depends`** is how the API layer *gets* its collaborators: a connection, a repository, the current user. It's the wiring. Keep the rules out of dependency functions too, or they become a hidden service layer that's hard to find.

A typical layout:

```text
app/
  main.py            # FastAPI(), include_router(...)
  api/stock.py       # APIRouter, request/response models, error mapping
  services/stock.py  # rules and the transaction boundary
  repos/stock.py     # SQL / SQLAlchemy queries
```

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "A teammate moved every endpoint into `APIRouter` modules and says the app is now layered. What's still missing?",
  "options": ["Nothing, routers are the layers", "The rules and the SQL still live inside the endpoint functions", "A Pydantic model for every response", "An abstract base class for each router"], "answer": 1,
  "explanation": "Routers split the API layer into files. Layering is about separating responsibilities: if each endpoint still runs SQL and checks rules, it's the same fat endpoint in more files." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Design review",
  "prompt": "Your adminpanel has a documented 'RPC vs direct-SQL' rule. Translate the idea to one Python service: an admin endpoint wants to ban a user. The users module has a service with `ban(user_id)` that also revokes sessions. The admin developer writes `UPDATE users SET banned = 1` directly from the admin repository because it's 'one line'. What do you say in review?",
  "model": "Call the users service, don't write its tables directly. The service's ban() owns the rule and the side effects (revoking sessions, audit, cache invalidation). Direct SQL bypasses them, so a banned user keeps their sessions. It also couples the admin code to the users table schema. The rule of thumb: a module's tables are written only through that module's service; direct reads for reporting can be an explicit, documented exception.",
  "explanation": "Writes go through the owner's service, because the service is where the invariants and side effects live." }
```

## 6. Your turn: split a fat endpoint

The exercise gives you a working registration endpoint with SQL, rules and HTTP mixed together. The API tests already pass. Keep them green while you move the SQL into a repository and the rules into a service. Some tests check the layer rules themselves (no SQL in `app.py` or `service.py`, no FastAPI below the API layer).

```exercise
ARCH.M01.L01.E1
```
