---
{
  "id": "ARCH.M01.L03",
  "title": "Protocols, fakes and what not to abstract",
  "difficulty": "intermediate",
  "minutes": 100,
  "prerequisites": ["ARCH.M01.L02"],
  "objectives": [
    "Declare a repository dependency with typing.Protocol and explain how it matches Go's implicit interfaces",
    "Predict what isinstance does with a runtime_checkable Protocol (method names only, no signatures)",
    "Write an in-memory fake and keep it honest with contract checks that also run against the real implementation",
    "Reject abstractions that have one implementation and no test need, and name the cost they carry"
  ],
  "why": "Good layering needs seams so the service can be tested without a database. Too many seams is its own failure: interfaces nobody swaps, factories for one product, base classes that hide simple SQL. This lesson gives you the tools for the seam and the judgement for when not to add one.",
  "applications": [
    "Fast service tests with an in-memory repository",
    "Faking external systems (payments, email, another team's API) in tests",
    "Reviewing pull requests that add 'flexibility' nobody asked for"
  ],
  "exercises": ["ARCH.M01.L03.E1"],
  "sources": [
    {
      "title": "typing: Protocol and runtime_checkable",
      "url": "https://docs.python.org/3.12/library/typing.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Protocol classes are used with static type checkers that recognise structural subtyping (static duck-typing)", "runtime_checkable checks only the presence of the required methods or attributes, not their type signatures"]
    },
    {
      "title": "PEP 544: Protocols: Structural subtyping (static duck typing)",
      "url": "https://peps.python.org/pep-0544/",
      "version": "PEP 544 (Final, Python 3.8)",
      "verified": "2026-11-12",
      "claims": ["A class that is a structural subtype of a protocol implements it", "Subclassing a protocol explicitly is possible but not necessary for type checking"]
    },
    {
      "title": "Go Code Review Comments: Interfaces",
      "url": "https://go.dev/wiki/CodeReviewComments",
      "version": "Go wiki (living page)",
      "verified": "2026-11-12",
      "claims": ["Go interfaces generally belong in the package that uses values of the interface type", "Do not define interfaces on the implementor side for mocking", "Do not define interfaces before they are used"]
    },
    {
      "title": "Yagni",
      "url": "https://martinfowler.com/bliki/Yagni.html",
      "version": "Martin Fowler, bliki (2015)",
      "verified": "2026-11-12",
      "claims": ["A capability presumed to be needed in the future should not be built now", "Presumptive features carry costs of build, delay, carry and repair", "YAGNI does not apply to effort that makes software easier to modify"]
    }
  ]
}
---
## 1. Protocol: Go interfaces, in Python

In Go, a type satisfies an interface just by having the methods. Nobody writes `implements`. `typing.Protocol` gives Python the same idea. The docs call it **structural subtyping** ("static duck-typing"):

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class PriceSource(Protocol):
    def price_of(self, sku: str) -> int: ...


class CatalogDB:                      # never mentions PriceSource
    def price_of(self, sku: str) -> int:
        return 1250


class Broken:
    def price_of(self):               # wrong signature, same name
        return "free"


def total(prices: PriceSource, skus: list[str]) -> int:
    return sum(prices.price_of(s) for s in skus)


print(total(CatalogDB(), ["A", "B"]))
print(isinstance(CatalogDB(), PriceSource), isinstance(Broken(), PriceSource), isinstance("x", PriceSource))
```

```console
$ python proto_demo.py
2500
True True False
```

What to take from it:

- `CatalogDB` satisfies `PriceSource` without inheriting from it. PEP 544 says subclassing a protocol is possible "but not necessary".
- **Protocols are checked by type checkers, not at runtime.** Python happily runs `total(Broken(), ...)` and fails later. With `@runtime_checkable`, `isinstance` checks only that the method *names* exist, which is why `Broken` passes. The docs say exactly this: it checks "the presence of the required methods or attributes, not their type signatures".

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Protocol, runtime_checkable\n\n@runtime_checkable\nclass Mailer(Protocol):\n    def send(self, to: str, body: str) -> None: ...\n\nclass Smtp:\n    def send(self, to, body):\n        pass\n\nclass Printer:\n    def send(self):\n        pass\n\nclass Pigeon:\n    def deliver(self, to, body):\n        pass\n\nprint([isinstance(x, Mailer) for x in (Smtp(), Printer(), Pigeon())])",
  "answer": "[True, True, False]",
  "explanation": "runtime_checkable only checks that a `send` attribute exists. Printer.send has the wrong parameters and still passes. Pigeon has no send at all. Signatures are the type checker's job, not isinstance's." }
```

## 2. Put the Protocol where it's used

Go's code review guide says interfaces "generally belong in the package that uses values of the interface type", and warns: "Do not define interfaces before they are used". The same advice works in Python:

- The **service** module declares the small Protocol it needs (`get_item`, `set_on_hand`), not the repository module.
- It lists only the methods the service calls. A 2-method Protocol is easy to fake; a 15-method "repository interface" isn't.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "`checkout_service` only calls `get_cart(user_id)` and `clear_cart(user_id)` on the cart repository, which has 12 methods. What Protocol should the service depend on?",
  "options": ["A Protocol with all 12 methods, defined next to the repository", "A Protocol with `get_cart` and `clear_cart`, defined in the service module", "No type at all, to keep it flexible", "An abstract base class the repository must inherit from"], "answer": 1,
  "explanation": "Depend on what you use, and declare it at the consumer. The fake for the tests then needs two methods, and the real repository satisfies it without changing." }
```

## 3. Fakes, and how they lie

The point of the seam is testing: give the service an in-memory **fake** instead of a database. The risk is that a fake is a second implementation, and it can quietly behave differently from the real one. Then your service tests pass against behaviour production doesn't have.

The defence is a set of **contract checks**: one set of expectations, run against *every* implementation:

```python
class SqlitePriceRepo:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE prices (sku TEXT PRIMARY KEY COLLATE NOCASE, cents INTEGER)")

    def set_price(self, sku, cents):
        self.conn.execute("INSERT OR REPLACE INTO prices VALUES (?, ?)", (sku, cents))

    def get_price(self, sku):
        row = self.conn.execute("SELECT cents FROM prices WHERE sku = ?", (sku,)).fetchone()
        return None if row is None else row[0]


class DictPriceRepo:
    def __init__(self):
        self.prices = {}

    def set_price(self, sku, cents):
        self.prices[sku] = cents

    def get_price(self, sku):
        return self.prices.get(sku)


def check_contract(repo):
    """The same expectations, run against every implementation."""
    repo.set_price("BOLT-8", 120)
    problems = []
    if repo.get_price("BOLT-8") != 120:
        problems.append("exact sku")
    if repo.get_price("bolt-8") != 120:
        problems.append("sku is case-insensitive")
    if repo.get_price("NUT-1") is not None:
        problems.append("missing sku gives None")
    return problems or "ok"


for repo in (SqlitePriceRepo(), DictPriceRepo()):
    print(type(repo).__name__, check_contract(repo))
```

```console
$ python drift.py
SqlitePriceRepo ok
DictPriceRepo ['sku is case-insensitive']
```

`COLLATE NOCASE` in the real table makes lookups case-insensitive; the dict doesn't. A service test using the fake would never see that `"bolt-8"` finds the price in production. The contract check found the drift in one run.

**Common fake mistakes:** forgetting a constraint the database enforces (unique, case rules), returning the stored object itself so callers can mutate the fake's state, and adding features the real repository doesn't have.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "If all service tests pass against an in-memory fake, the service is proven to work with the real database repository.", "answer": false,
  "explanation": "They prove it works with the fake. You still need contract checks (or integration tests, WEB.M05) against the real repository to know the two behave the same." }
```

## 4. What not to abstract

Every seam has a price. Fowler's YAGNI article names the costs of building something "we presume our software needs in the future": the cost of building it, the delay to things you could have shipped instead, the **cost of carry** (the added complexity slows every later change), and the cost of repair when the guess was wrong.

Common examples in Python backends:

| Looks flexible | What it really is |
|---|---|
| `AbstractUserRepository(ABC)` + `SqlUserRepository` + `RepositoryFactory`, one database forever | Three names to read for one class. Add the Protocol when a second implementation (or a test fake you actually use) exists. |
| A generic `BaseRepository[T]` with `get/list/create/update/delete` for every table | Hides the SQL you need to tune, and forces every table into the same CRUD shape. Write the five queries the service uses. |
| A service function that only forwards to the repository (`def get_user(id): return repo.get(id)`) | Ceremony. Fine to keep for consistency in a team convention, but don't invent rules to fill it. |
| Configuration for a value that never changes | An `if` nobody tests. |

**When a seam pays for itself:**

- The dependency is **external or slow**: a payment provider, an email service, another team's API. You need to control it in tests.
- A **second implementation exists now**, such as a fake that the tests use, or two storage backends.
- The boundary **will be tested heavily** and the real thing is awkward to set up.

YAGNI isn't an excuse for messy code, though. The same article says it "does not apply to effort to make the software easier to modify". Keeping layers clean (L01) is that kind of effort. Speculative interfaces aren't.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "Which new abstraction is easiest to justify today?",
  "options": ["A `StorageBackend` interface so the app could move from PostgreSQL to MongoDB later", "A `PaymentGateway` Protocol with the real payment-provider client and an in-memory fake used by 30 tests", "A `BaseService` class that every service must inherit from", "A plugin system for the two report formats you have"], "answer": 1,
  "explanation": "The payment seam has two implementations in use right now, and it isolates an external, slow, side-effecting system in tests. The others are presumptive: there's no second implementation, only a guess." }
```

```quiz
{ "id": "q5", "type": "explain", "label": "Design review",
  "prompt": "A PR for a 400-line FastAPI service adds `interfaces/`, `factories/` and `adapters/` folders: `IOrderRepository`, `OrderRepositoryFactory`, `SqlOrderRepositoryAdapter`. There is one database and no fake in the tests (tests use SQLite). The author says it's 'clean architecture'. What do you say?",
  "model": "Ask what each piece buys today. There's one implementation and the tests don't swap it, so the interface, the factory and the adapter are presumptive. They add files and indirection to every change (the cost of carry) without enabling a single test. Suggest one concrete OrderRepo class used directly by the service. Add a Protocol at the service when a second implementation (for example a fake for a slow dependency) actually appears. Clean layering is about responsibilities and dependency direction, not about the number of abstraction folders.",
  "explanation": "Abstractions are justified by a second implementation or a testing need that exists now." }
```

## 5. Your turn: a fake that keeps the contract

You'll write an in-memory user repository. The same contract checks run against the real SQLite repository (they already pass) and against your fake. Watch for case-insensitive emails, ids after a rejected duplicate, and aliasing.

```exercise
ARCH.M01.L03.E1
```
