```sql
-- ADD_USER
INSERT INTO users (username, created_at) VALUES (?, ?)

-- EDIT_MESSAGE
UPDATE messages SET body = ?, edited_at = ? WHERE id = ?

-- LEAVE_CHAT
DELETE FROM chat_members WHERE chat_id = ? AND user_id = ?
```

**Why it works**

- **ADD_USER:** `INSERT INTO users VALUES (?, ?)` must supply every column in table order, and users has three (`id`, `username`, `created_at`), so SQLite refuses it: "table users has 3 columns but 2 values were supplied". With a column list, the omitted `id` (an INTEGER PRIMARY KEY) is assigned by SQLite, and `cursor.lastrowid` tells you which. A column list also keeps the statement correct when someone adds a column later.
- **EDIT_MESSAGE:** without WHERE, an UPDATE changes every row. Here it failed earlier because there were only two placeholders for three parameters; if someone had "fixed" that by dropping the id parameter, every message in the database would have been overwritten.
- **LEAVE_CHAT:** `chat_id = ? OR user_id = ?` matches all members of chat 1 *and* all of user 2's memberships: 5 rows. Leaving a chat means both conditions at once: AND.
- **rowcount 0 is not an error.** Like `RowsAffected()` in Go, it's your job to check it. An API would turn rowcount 0 into "404 message not found".

**Alternative:** SQLite (since 3.35.0) supports `RETURNING`, which hands back the changed rows from the same statement, e.g. `UPDATE ... WHERE id = ? RETURNING id, body`. Not every database has it, so the habit of checking rowcount transfers everywhere, including MySQL.
