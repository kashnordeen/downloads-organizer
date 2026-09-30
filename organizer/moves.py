import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

from .core import safe_path, signature


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class Journal:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY, source TEXT, destination TEXT, state TEXT,
            hash TEXT, signature TEXT, temp TEXT, undo_of INTEGER, error TEXT)""")
        self.db.commit()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.db.close()

    def update(self, operation, **fields):
        keys = list(fields)
        self.db.execute("UPDATE operations SET " + ",".join(k + "=?" for k in keys) + " WHERE id=?",
                        [fields[k] for k in keys] + [operation])
        self.db.commit()

    def history(self):
        return self.db.execute("SELECT id,source,destination,state,error FROM operations ORDER BY id DESC").fetchall()

    def move(self, proposal, undo_of=None):
        source = safe_path(proposal.source)
        if proposal.destination is None or proposal.signature != signature(source):
            raise ValueError("File changed since preview; preview again")
        if time.time_ns() - source.stat().st_mtime_ns < 2_000_000_000:
            raise ValueError("File is still new; wait for the download to finish")
        destination = safe_path(proposal.destination)
        if destination == source:
            raise ValueError("Source and destination are identical")
        expected = digest(source)
        if signature(source) != proposal.signature:
            raise ValueError("File changed while reading")
        cursor = self.db.execute("""INSERT INTO operations
            (source,destination,state,hash,signature,undo_of,error)
            VALUES (?,?,'pending',?,?,?, '')""", (str(source), str(destination), expected,
                json.dumps(proposal.signature), undo_of))
        operation = cursor.lastrowid
        self.db.commit()
        temp = None
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            safe_path(destination.parent)
            fd, name = tempfile.mkstemp(prefix=".organizer-", suffix=".tmp", dir=destination.parent)
            temp = Path(name)
            self.update(operation, temp=str(temp))
            with os.fdopen(fd, "wb") as target, source.open("rb") as origin:
                shutil.copyfileobj(origin, target, 1024 * 1024)
                target.flush()
                os.fsync(target.fileno())
            if digest(temp) != expected or signature(source) != proposal.signature or digest(source) != expected:
                raise ValueError("Source changed during copy; original retained")
            shutil.copystat(source, temp)
            number = 0
            while True:
                candidate = destination if not number else destination.with_name(
                    f"{destination.stem} ({number}){destination.suffix}")
                self.update(operation, destination=str(candidate))
                try:
                    # Atomic no-overwrite publication. Fail safely on filesystems without hard links.
                    os.link(temp, candidate)
                    break
                except FileExistsError:
                    number += 1
            self.update(operation, state="published", signature=json.dumps(signature(candidate)))
            if signature(source) != proposal.signature or digest(source) != expected:
                raise ValueError("Source changed; both copies retained for review")
            # ponytail: readiness is heuristic; downloader-specific completion signals if needed.
            source.unlink()
            temp.unlink()
            self.update(operation, state="complete", temp="")
            if undo_of is not None:
                self.update(undo_of, state="undone")
            return candidate
        except Exception as error:
            self.update(operation, state="review", error=str(error))
            raise
