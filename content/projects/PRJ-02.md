# PRJ-02: Message store library on SQLite

Starts after DB.M04. Estimated 12 h. Draft spec, to be confirmed with the learner when DB.M04 is done.

1. **Problem:** build `msgstore`, a small Python library (no web layer) that stores users, chats, chat members and
   messages in SQLite. Other code calls it through a repository API. The hard part is the delete-user operation:
   it is several writes that must happen all together or not at all. This revisits the Q-round answer "both DELETEs are
   done anyway" (`ASSESSMENT_HISTORY.md`).
   - Rule: the learner writes all the code and tests. The mentor reviews only after an attempt and never supplies the
     implementation.
2. **Functional requirements:**
   - **Users:**
     - `create_user(username)` returns the new user.
     - The username is trimmed, must be 1–32 characters, and is unique ignoring ASCII case. A duplicate raises
       `DuplicateError`; an invalid one raises `ValidationError`.
   - **Chats:**
     - `create_chat(title, creator_id, member_ids)`: the creator is always a member.
     - `add_member(chat_id, user_id)`: adding an existing member raises `DuplicateError`.
     - `remove_member(chat_id, user_id)`.
     - `list_chats(user_id)`: only the chats the user is a member of.
   - **Messages:**
     - `send_message(chat_id, sender_id, text)`:
       - The sender must be a member, or `NotAMemberError` is raised.
       - Text that is blank or whitespace-only raises `ValidationError`, as does text longer than 4000 characters.
       - Accepted text is stored exactly as given, including quotes, `%`, `_`, emoji and newlines.
     - `list_messages(chat_id, limit=50, before_id=None)`:
       - Returns messages newest first. `limit` must be 1–100.
       - `before_id` pages backwards (keyset pagination, not `OFFSET`).
       - A `before_id` that isn't a message in this chat raises `NotFoundError`.
     - `search_messages(chat_id, term)`:
       - Case-insensitive substring search.
       - `%` and `_` in `term` match literally, not as wildcards.
       - Decide what "case-insensitive" means for non-ASCII text, document it, and pin it with a test. Look it up in
         the SQLite docs for `LIKE`; don't guess.
   - **`delete_user(user_id)`:** removes in **one transaction**:
     - the user
     - their memberships
     - their messages
     - any chat left with no members

     If any step fails, nothing changes.
   - **Errors:** unknown ids raise `NotFoundError`. Every error is a domain exception from your own hierarchy
     (PY.M04). No raw `sqlite3` exception leaks to callers.
   - **Return types:** results are dataclasses (PY.M05), not tuples or `sqlite3.Row`.
3. **Non-functional:**
   - **Tools:** standard library (`sqlite3`) and pytest only. No ORM; that comes in DB.M07.
   - **Placeholders for every value** in every SQL statement. Table and column names can't be placeholders, so any
     that vary (for example a sort order) must come from a fixed allow-list.
   - **Foreign keys enforced on every connection.** On this machine's SQLite (3.45.1), `PRAGMA foreign_keys` reads 0
     on a new connection (checked 2026-11-12), so enforcement is your job.
   - **Schema created by code:**
     - Create the schema from a `.sql` file through one `init_schema` function.
     - Running it twice is safe.
     - Record the schema version in `PRAGMA user_version`.
   - **Library behaviour:** no `print` calls; type hints on the public API.
   - **Performance:** with 100k messages in one chat, measure how long `list_messages` takes for the first and the
     last page, and write the numbers in the README. No target is promised; DB.M05 comes back to this with indexes.
   - **Environment:** everything runs on this machine (Python 3.12.3, stdlib `sqlite3`). Nothing needs installing.
4. **Architecture:**
   - **Before coding**, the learner writes a one-page proposal (`DESIGN.md`) with these sections:
     - Tables: columns, primary keys, `UNIQUE`/`NOT NULL`/`CHECK`/foreign-key constraints, and why each exists.
     - Public API: function signatures and the exceptions each one raises.
     - Who opens, commits and closes connections, and where the transaction for `delete_user` begins and ends.
     - How `sqlite3` errors are mapped to domain errors.
   - **Required restatement:** 3–5 sentences explaining what happens if the process crashes between two `DELETE`
     statements, first in autocommit mode and then inside one transaction. Use your DB.M03 notes, and correct the
     Q-round answer in your own words.
   - **Questions the mentor will ask** (answer them in review; don't look for model answers):
     - `ON DELETE CASCADE` or explicit deletes: what does each one hide or make visible?
     - Should the repository commit, or the caller? What breaks when two repository calls must be atomic together?
     - Is "unique ignoring case" enforced by the database or by Python? What happens when two processes insert at
       once?
   - **Interface sketch** (the shape only; names may change in your proposal):
     ```python
     store = MessageStore.open("app.db")   # or MessageStore(conn)
     alice = store.create_user("alice")
     chat = store.create_chat("team", creator_id=alice.id, member_ids=[])
     store.send_message(chat.id, alice.id, "hi")
     page = store.list_messages(chat.id, limit=20)          # list[Message], newest first
     older = store.list_messages(chat.id, limit=20, before_id=page[-1].id)
     store.delete_user(alice.id)                            # all or nothing
     ```
5. **Milestones:**
   - Each milestone ends when its "done" checks are met **and** `pytest` is green locally.
   - Hours are estimates (12 h in total).
   - **M0 proposal (1 h).** Done when:
     - `DESIGN.md` and the crash restatement are written.
     - The mentor has reviewed them, and the learner has answered the challenge questions.
   - **M1 schema and connection (2 h).** Done when:
     - `init_schema` is idempotent and sets `user_version`.
     - A test proves that foreign keys are enforced.
     - Tests show that each constraint rejects bad rows: duplicate username, a message for a missing chat, empty text
       if you enforce it with `CHECK`.
   - **M2 users and chats (2 h).** Done when all user and chat functions work, with tests for:
     - duplicates, including a case-only difference (`Alice` vs `alice`)
     - unknown ids
     - a creator who is also passed in `member_ids`
     - `list_chats` for a user with no chats
   - **M3 messages (3 h).** Done when:
     - `send_message`, `list_messages` and `search_messages` pass tests for:
       - a non-member sender
       - blank, whitespace-only and 4001-character text
       - `limit` values 0, 1, 100 and 101
       - an empty chat
       - the exact page boundary (exactly `limit` messages)
       - a `before_id` that doesn't exist
       - search terms containing `%`, `_` and `'`
     - The 100k-message timing is in the README.
   - **M4 transactional delete-user (2.5 h).** Done when:
     - `delete_user` works.
     - The rollback tests in §6 pass.
     - The learner can point to the exact line where the transaction begins and ends.
   - **M5 final review (1.5 h).** Done when:
     - The mentor acceptance suite has been run.
     - The code review is done and the self-review is written.
     - Evidence is recorded (§9).
6. **Testing:**
   - **Order:** write tests before each milestone's code.
   - **Isolation:** each test gets a fresh database (`:memory:` or pytest's `tmp_path`). No test depends on another
     test's data.
   - **Required rollback tests:**
     - **Failure injected mid-way:**
       - Force `delete_user` to fail after its first write. How you inject the failure is a design decision you
         defend in review.
       - Assert that the user, their memberships and their messages are all still there.
     - **Second connection:**
       - With a file database, open a second connection after the failed delete.
       - Assert that it sees the original data. This rules out "rolled back only in my connection's view".
     - **Success case:** after a successful delete, nothing of the user is left, and a chat whose last member was
       the user is gone.
   - **Required safe-SQL tests:**
     - Usernames and texts such as `O'Brien`, `'); DROP TABLE users;--`, `100%_done` and `"quoted"` are stored and
       read back unchanged.
     - The tables still exist afterwards.
   - **Evidence:**
     - Run `pytest --junitxml=result.xml` locally and bring the report to the review session.
     - The site's JUnit import only accepts exercise ids, so project results are recorded by the mentor, not
       imported.
7. **Security:**
   - **SQL injection:**
     - Every value goes through a placeholder.
     - Any SQL text built from a value with an f-string, `%`, `+` or `.format()` **fails the project**, whatever the
       points total.
     - The mentor checks this by reading every `execute` call.
   - **`LIKE` wildcards:** treat user search terms as data. Escape `%` and `_` with an `ESCAPE` clause, while the
     term itself stays a placeholder value.
   - **Untrusted input:** all text is stored verbatim and never interpreted. Validation errors don't echo more than
     needed.
   - **Integrity:**
     - Foreign keys stay on.
     - A failed delete-user must never leave a half-deleted user. Messages without a user are a data-integrity bug,
       not a cosmetic one.
8. **Rubric (100 points):**
   - Correctness on the mentor acceptance suite: 35. The suite is written when the project starts and run at M5;
     keeping it unseen relies on honesty.
   - Transaction design and the rollback tests: 15
   - Learner's tests (edge cases, isolation, readability): 15
   - Schema and constraints (correct keys, constraints justified in `DESIGN.md`): 15
   - Safe SQL (placeholders, `LIKE` escaping, allow-listed identifiers): 10
   - Clarity and error handling (domain exceptions, dataclasses, small functions): 10
   - **Pass** = all of the following:
     - 70 or more
     - all core acceptance tests pass
     - no value-interpolated SQL
     - both rollback tests present and passing
9. **Final review:**
   - Code review in mentor review mode, plus a short self-review: what you'd change, and which edge case you nearly
     missed.
   - **Evidence that counts:**
     - your tests passing locally (the JUnit report)
     - the mentor acceptance suite run in the session
     - your answers to the challenge questions
   - Code written with AI help doesn't count.
   - The mentor records scores and evidence in `ASSESSMENT_HISTORY.md` and `content/learner/assessments.json`. The
     record covers the transactions and safe-SQL competencies, rated on dimensions B (implementation) and C
     (debugging).
