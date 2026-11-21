"""Real file/SQLite effects behind the existing finite permission vocabulary."""

import json
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

RESOURCES = ("notes/project", "notes/meeting", "calendar/work", "calendar/personal")


class Store:
    def __init__(self, root: Path, backend="files", initial=None):
        self.root, self.backend = root, backend
        self.paths = {name: root / (name.replace("/", "-") + ".txt") for name in RESOURCES}
        self.db = sqlite3.connect(root / "notes.db", check_same_thread=False)
        self.db.execute("CREATE TABLE notes(resource TEXT PRIMARY KEY, content TEXT NOT NULL)")
        self.outbox = root / "outbox.jsonl"
        for resource, content in (initial or {name: "original" for name in RESOURCES}).items():
            self.paths[resource].write_text(content, encoding="utf-8")
            self.db.execute("INSERT INTO notes VALUES (?, ?)", (resource, content))
        self.db.commit()

    def read(self, resource):
        self.paths[resource]  # fixed resource identifiers never become caller-controlled paths
        if self.backend == "files":
            path = self.paths[resource]
            return path.read_text(encoding="utf-8") if path.exists() else None
        row = self.db.execute("SELECT content FROM notes WHERE resource=?", (resource,)).fetchone()
        return None if row is None else row[0]

    def write(self, resource, content):
        path = self.paths[resource]
        if self.backend == "files":
            path.write_text(content, encoding="utf-8")
        else:
            self.db.execute("UPDATE notes SET content=? WHERE resource=?", (content, resource))
            self.db.commit()

    def delete(self, resource):
        path = self.paths[resource]
        if self.backend == "files":
            path.unlink(missing_ok=True)
        else:
            self.db.execute("DELETE FROM notes WHERE resource=?", (resource,))
            self.db.commit()

    def snapshot(self):
        return {
            "resources": {name: self.read(name) for name in RESOURCES},
            "outbox": self.outbox.read_text(encoding="utf-8") if self.outbox.exists() else "",
        }

    def close(self):
        self.db.close()


def build_server(store):
    server = FastMCP("clamp-real-effects")

    def notes_read(resource: str) -> str:
        return store.read(resource) or ""

    def notes_write(resource: str, content: str) -> str:
        store.write(resource, content)
        return "saved"

    def notes_delete(resource: str) -> str:
        store.delete(resource)
        return "deleted"

    def mail_send(to: str, subject: str, body: str) -> str:
        # ponytail: local delivery sink; no external SMTP is needed to observe egress.
        with store.outbox.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"to": to, "subject": subject, "body": body}) + "\n")
        return "delivered to local sink"

    for name, fn in {
        "notes.read": notes_read,
        "notes.write": notes_write,
        "notes.delete": notes_delete,
        "calendar.read": notes_read,
        "mail.send": mail_send,
    }.items():
        server.add_tool(fn, name=name)
    return server
