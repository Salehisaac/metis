"""Move money between wallets: all or nothing."""
import sqlite3

SCHEMA = "CREATE TABLE accounts (id INTEGER PRIMARY KEY, balance INTEGER NOT NULL)"


class AccountNotFound(Exception):
    pass


class InsufficientFunds(Exception):
    pass


class AccountRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def balance(self, account_id: int) -> int | None:
        row = self.conn.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return None if row is None else row[0]

    def deposit(self, account_id: int, amount: int) -> bool:
        """Add amount; False if there is no such account."""
        cur = self.conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
        self.conn.commit()  # save it right away
        return cur.rowcount == 1

    def withdraw(self, account_id: int, amount: int) -> bool:
        """Subtract amount only if the balance covers it, in ONE conditional UPDATE.

        Returns False (and changes nothing) if the account is missing or the balance is too low.
        """
        raise NotImplementedError


class UnitOfWork:
    """with UnitOfWork(conn) as uow: ... uses uow.accounts.

    Commit when the block finishes normally, roll back when it raises, and never swallow the exception.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.accounts = AccountRepo(conn)

    def __enter__(self):
        raise NotImplementedError

    def __exit__(self, exc_type, exc, tb):
        raise NotImplementedError


def transfer(conn: sqlite3.Connection, from_id: int, to_id: int, amount: int) -> None:
    """Move amount (a positive int) from one account to another inside one UnitOfWork.

    ValueError: amount <= 0, or from_id == to_id.
    AccountNotFound: either account is missing.
    InsufficientFunds: from_id's balance is lower than amount.
    On any error, no balance changes.
    """
    raise NotImplementedError
