```python
NEW_TITLE = {"title": "renamed"}

CASES = [
    pytest.param(ALI, "GET", "/chats/1/members", None, 200, id="member-lists-members"),
    pytest.param(None, "GET", "/chats/1/members", None, 401, id="anonymous-lists-members"),
    pytest.param(BAD_TOKEN, "GET", "/chats/1/members", None, 401, id="bad-token-lists-members"),
    pytest.param(ROOT, "GET", "/chats/1/members", None, 200, id="admin-lists-members"),
    pytest.param(EVE, "GET", "/chats/1/members", None, 404, id="outsider-lists-members"),
    # rename
    pytest.param(OLGA, "PATCH", "/chats/1", NEW_TITLE, 200, id="owner-renames"),
    pytest.param(ROOT, "PATCH", "/chats/1", NEW_TITLE, 200, id="admin-renames"),
    pytest.param(ALI, "PATCH", "/chats/1", NEW_TITLE, 403, id="member-renames"),
    pytest.param(EVE, "PATCH", "/chats/1", NEW_TITLE, 404, id="outsider-renames"),
    pytest.param(None, "PATCH", "/chats/1", NEW_TITLE, 401, id="anonymous-renames"),
    # remove member
    pytest.param(OLGA, "DELETE", "/chats/1/members/2", None, 204, id="owner-removes-member"),
    pytest.param(ROOT, "DELETE", "/chats/1/members/2", None, 204, id="admin-removes-member"),
    pytest.param(ALI, "DELETE", "/chats/1/members/2", None, 204, id="member-leaves"),
    pytest.param(ALI, "DELETE", "/chats/1/members/3", None, 403, id="member-removes-other"),
    pytest.param(ROOT, "DELETE", "/chats/1/members/1", None, 403, id="admin-removes-owner"),
    pytest.param(EVE, "DELETE", "/chats/1/members/2", None, 404, id="outsider-removes-member"),
    pytest.param(None, "DELETE", "/chats/1/members/2", None, 401, id="anonymous-removes-member"),
]
```

**Which row kills which mutant**

| Mutant | Killed by |
|---|---|
| `member_can_rename` | `member-renames` (403 expected, mutant gives 200) |
| `admin_cannot_rename` | `admin-renames`: an *allowed* row. A table with only denied rows misses checks that are too strict |
| `outsider_gets_403` | any outsider row (`outsider-lists-members`, `outsider-renames`, ...) |
| `bad_token_is_403` | `bad-token-lists-members`. The anonymous rows can't catch it, because OAuth2PasswordBearer answers a missing header before `get_current_user` runs |
| `member_removes_others` | `member-removes-other` |
| `owner_can_be_removed` | `admin-removes-owner` |
| `outsider_lists_members` | `outsider-lists-members` |

**Why it works**

- **A grid, not a list of ideas.** Callers × endpoints, each cell filled from the rules. Gaps become visible: "did I test the admin on remove?" has a yes/no answer.
- **Allowed rows matter.** Authorization bugs go both ways. Too permissive is a security hole (your admin-panel story); too strict is an outage for admins or owners.
- **401 has two paths.** A missing header and an invalid token are rejected by different code, so each needs a row. The same goes for 404 (chat missing vs chat invisible) when both exist.

**Alternative:** generate the grid with nested parametrize (`@pytest.mark.parametrize("actor", ...)` × `@pytest.mark.parametrize("endpoint", ...)`) and an `expected(actor, endpoint)` function. That's shorter, but the function re-implements the rules, and a bug in it hides the same bug in the app. An explicit table is easier to review.
