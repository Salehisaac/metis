# Reference solution

`update_email` after the fix (the rest of `users.py` is unchanged):

```python
def update_email(conn: sqlite3.Connection, r, user_id: int, email: str) -> None:
    """Change the user's email, then make sure readers stop seeing the old one.

    - The database is the source of truth: once the UPDATE is committed, the change counts as done.
    - Raise UserNotFound if there is no such user.
    """
    email = email.strip().lower()
    with conn:
        cur = conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
    if cur.rowcount == 0:
        raise UserNotFound(user_id)
    # Committed. Only now is it safe to drop the cached copy.
    key = user_key(user_id)
    try:
        r.delete(key)
    except redis.RedisError as e:
        # The change is done; the stale copy expires within USER_TTL. Say so loudly instead of hiding it.
        log.warning("cache invalidation failed for %s (stale for up to %ss): %s", key, USER_TTL, e)

```

**The three bugs**

1. **Wrong key.** It deleted `user:1`, but `get_user` reads `cache:user:1`. The delete "worked" (it returned 0) and readers kept the old email for the full TTL. Building the key in one function (`user_key`) makes this impossible.
2. **Delete before commit.** Between the delete and the commit, a concurrent reader misses, reads the *old* committed row and caches it again. The invalidation is wasted and the stale copy lives for another full TTL. The test catches it by looking at the database from a second connection at the moment of the delete.
3. **`except Exception: pass`.** When Redis is down, the copy stays stale and nothing records that. Worse, it would also hide a genuine bug (the `TypeError` test). Catching `redis.RedisError` and logging the key turns a silent inconsistency into something you can see and alert on.

**Why not fail the request when the delete fails?** The commit already happened. Returning an error would tell the client the email change failed when it didn't, and a retry would change it again. The TTL bounds the damage (at most `USER_TTL` seconds stale). If even that is unacceptable, record the invalidation in the same transaction and let a worker retry it (the outbox, ARCH.M03).

**Alternatives**

- Write the new value into the cache instead of deleting. The redis.io guide advises deleting instead, because keeping the cache in sync from the application "opens the door to subtle ordering bugs". One such bug: two concurrent writers set their values in the opposite order to their commits, leaving the older value cached.
- A short "delayed second delete" (delete again a second later) narrows the remaining race from L02 section 3. It adds a timer for a rare case, so reach for it only when stale reads are actually reported.
