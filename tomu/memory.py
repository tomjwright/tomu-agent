"""Memory: what the agent keeps between turns, in one SQLite file.

    history   every past message and reply, so the agent can follow a conversation
    facts     short things worth keeping about the user ("Tom lives in Singapore"),
              searched with SQLite's built-in full-text search (FTS5)

Before each turn the retrieval gate decides whether looking up facts is worth it:
it searches only when the message has words worth searching for, so "hi" or
"thanks" skip the lookup entirely.
"""

import re
import sqlite3
import time

from tomu.tools import Tool

SCHEMA = """
CREATE TABLE IF NOT EXISTS history (role TEXT, content TEXT, saved_at REAL);
CREATE VIRTUAL TABLE IF NOT EXISTS facts USING fts5(text, saved_at UNINDEXED);
CREATE TABLE IF NOT EXISTS consolidation (last_rowid INTEGER);
"""

# Words too common to say anything about what the user is asking for.
STOPWORDS = set(
    "the and for are but not you your yours with what when where who why how this that "
    "these those have has had was were will would can could should does did done from "
    "into about just like then than them they their there here its it's i'm ive also "
    "hi hey hello thanks thank please okay yes yeah sure".split()
)


class Memory:
    def __init__(self, path: str):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.executescript(SCHEMA)
        return db

    def history(self, limit: int = 20) -> list[dict]:
        """The last `limit` messages, oldest first, ready to send to the model."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT role, content FROM history ORDER BY rowid DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

    def save_turn(self, message: str, reply: str) -> None:
        now = time.time()
        with self.connect() as db:
            db.executemany(
                "INSERT INTO history VALUES (?, ?, ?)",
                [("user", message, now), ("assistant", reply, now)],
            )

    def unconsolidated(self) -> tuple[list[dict], int, int]:
        """Messages saved since the last consolidation, the row id where that one
        stopped, and the row id of the newest message."""
        with self.connect() as db:
            done = db.execute("SELECT MAX(last_rowid) FROM consolidation").fetchone()[0] or 0
            rows = db.execute(
                "SELECT rowid, role, content FROM history WHERE rowid > ? ORDER BY rowid", (done,)
            ).fetchall()
        newest = rows[-1][0] if rows else done
        return [{"role": role, "content": content} for _, role, content in rows], done, newest

    def claim(self, done: int, newest: int) -> bool:
        """Mark messages up to `newest` as consolidated, unless another consolidation
        (say, from Telegram) moved the mark past `done` first. False if it did."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")  # nobody else can move the mark meanwhile
            mark = db.execute("SELECT COALESCE(MAX(last_rowid), 0) FROM consolidation")
            if mark.fetchone()[0] != done:
                return False
            db.execute("INSERT INTO consolidation VALUES (?)", (newest,))
        return True

    def release(self, newest: int) -> None:
        """Undo a claim, so those messages are consolidated next time."""
        with self.connect() as db:
            db.execute("DELETE FROM consolidation WHERE last_rowid = ?", (newest,))

    def all_facts(self) -> list[str]:
        with self.connect() as db:
            return [text for (text,) in db.execute("SELECT text FROM facts ORDER BY rowid")]

    def remember(self, fact: str) -> str:
        with self.connect() as db:
            db.execute("INSERT INTO facts VALUES (?, ?)", (fact, time.time()))
        return f"Remembered: {fact}"

    def recall(self, message: str, limit: int = 5) -> list[str] | None:
        """The retrieval gate. Returns None when the gate skips the lookup,
        otherwise the best-matching facts (possibly none)."""
        words = {w for w in re.findall(r"\w+", message.lower()) if len(w) > 2}
        words -= STOPWORDS
        if not words:
            return None
        query = " OR ".join(f'"{w}"' for w in sorted(words))
        with self.connect() as db:
            rows = db.execute(
                "SELECT text FROM facts WHERE facts MATCH ? ORDER BY rank LIMIT ?",
                (query, limit),
            ).fetchall()
        return [text for (text,) in rows]


def remember_tool(memory: Memory) -> Tool:
    return Tool(
        name="remember",
        description=(
            "Save a short fact about the user for future conversations, e.g. "
            "'Tom lives in Singapore'. Use it when the user shares something worth keeping."
        ),
        input_schema={
            "type": "object",
            "properties": {"fact": {"type": "string", "description": "One short sentence."}},
            "required": ["fact"],
        },
        run=memory.remember,
    )
