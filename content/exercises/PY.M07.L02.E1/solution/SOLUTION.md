```python
@contextmanager
def lease(self):
    if not self.free:
        raise RuntimeError("pool exhausted")
    conn = self.free.pop(0)
    try:
        yield conn
    finally:
        self.free.append(conn)
```

**Why it works**

- `@contextmanager` runs the generator up to `yield` on enter, and the yielded value becomes `conn` in `with pool.lease() as conn`.
- When the block ends normally (or by `return`, which also leaves the block), the generator resumes after `yield` and the `finally` runs.
- When the block raises, the exception is re-raised **at the `yield`** inside the generator. The `finally` runs and the exception keeps propagating to the caller, because nothing catches it.
- **Acquire before `try`, release in `finally`.** If the pool is empty, the function raises before the `try` starts, so there is no `finally` to put back a connection that was never taken. Putting the acquisition inside the `try` is the classic bug: the `finally` then "returns" `None` (or crashes with an `UnboundLocalError`) and corrupts the pool. `test_exhausted_pool_is_not_corrupted` catches exactly that.

This is Go's pattern, too:

```go
conn, err := pool.Get()
if err != nil {
    return err          // nothing to release
}
defer pool.Put(conn)    // only after a successful Get
```

**Alternatives**

- A class with `__enter__`/`__exit__`. `__enter__` would pop and store the connection on an object, and `__exit__` would append it and return `False`. It needs a separate lease object per `with`, which is why the generator version is shorter here.
- A real pool would use a `queue.Queue` and block (with a timeout) instead of failing when empty, so it works across threads. This one is single-threaded on purpose.
