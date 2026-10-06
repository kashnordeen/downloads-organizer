import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

from .core import Proposal, safe_path, signature


class OperationCancelled(Exception):
    pass


def chunks(path, cancelled=None, progress=None):
    """Bounded reads keep both hashing and copying interruptible."""
    total, done, last = path.stat().st_size, 0, 0
    if progress:
        progress(0, total)
    with path.open("rb") as stream:
        while True:
            if cancelled and cancelled():
                raise OperationCancelled("Cancelled safely; original retained")
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            yield chunk
            done += len(chunk)
            now = time.monotonic()
            if progress and (now - last >= .1 or done >= total):
                progress(done, total)
                last = now
    if progress and not total:
        progress(0, 0)


def digest(path, cancelled=None, progress=None):
    result = hashlib.sha256()
    for chunk in chunks(path, cancelled, progress):
        result.update(chunk)
    return result.hexdigest()


class Journal:
    def __init__(self, path, cancelled=None, progress=None):
        self.cancelled, self.progress = cancelled, progress
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

    def check_cancel(self):
        if self.cancelled and self.cancelled():
            raise OperationCancelled("Cancelled safely; original retained")

    def progress_for(self, path, phase):
        return (lambda done, total: self.progress(path, phase, done, total)) if self.progress else None

    def digest(self, path, phase="Checking", display=None):
        return digest(path, self.cancelled, self.progress_for(display or path, phase))

    def finishing(self, path):
        self.check_cancel()
        if self.progress:
            self.progress(path, "Finishing", 0, 0)
        self.check_cancel()

    def history(self):
        return self.db.execute("SELECT id,source,destination,state,error FROM operations ORDER BY id DESC").fetchall()

    def unresolved_sources(self):
        return {row[0] for row in self.db.execute(
            "SELECT source FROM operations WHERE state IN ('pending','published','review','keep_pending')")}

    def kept_sources(self):
        return {source: tuple(json.loads(saved)) for source, saved in self.db.execute(
            "SELECT source,signature FROM operations WHERE state='kept'")}

    def move(self, proposal, undo_of=None):
        source = safe_path(proposal.source)
        if str(source) in self.unresolved_sources():
            raise ValueError("An earlier operation for this file needs review; no duplicate move attempted")
        if self.kept_sources().get(str(source)) == proposal.signature:
            raise ValueError("This file was left in Downloads after review")
        if proposal.destination is None or proposal.signature != signature(source):
            raise ValueError("File changed since preview; preview again")
        if time.time_ns() - source.stat().st_mtime_ns < 2_000_000_000:
            raise ValueError("File is still new; wait for the download to finish")
        destination = safe_path(proposal.destination)
        if destination == source:
            raise ValueError("Source and destination are identical")
        expected = self.digest(source)
        if signature(source) != proposal.signature:
            raise ValueError("File changed while reading")
        cursor = self.db.execute("""INSERT INTO operations
            (source,destination,state,hash,signature,undo_of,error)
            VALUES (?,?,'pending',?,?,?, '')""", (str(source), str(destination), expected,
                json.dumps(proposal.signature), undo_of))
        operation = cursor.lastrowid
        self.db.commit()
        temp = None
        published = False
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            safe_path(destination.parent)
            fd, name = tempfile.mkstemp(prefix=".organizer-", suffix=".tmp", dir=destination.parent)
            temp = Path(name)
            with os.fdopen(fd, "wb") as target:
                self.update(operation, temp=str(temp))
                for chunk in chunks(source, self.cancelled, self.progress_for(source, "Copying")):
                    target.write(chunk)
                if self.progress:
                    self.progress(source, "Flushing to disk", 0, 0)
                self.check_cancel()
                target.flush()
                os.fsync(target.fileno())
            if self.digest(temp, "Verifying copy", source) != expected or signature(source) != proposal.signature or self.digest(source, "Verifying original") != expected:
                raise ValueError("Source changed during copy; original retained")
            shutil.copystat(source, temp)
            number = 0
            while True:
                self.check_cancel()
                candidate = destination if not number else destination.with_name(
                    f"{destination.stem} ({number}){destination.suffix}")
                self.update(operation, destination=str(candidate))
                try:
                    # Atomic no-overwrite publication. Fail safely on filesystems without hard links.
                    os.link(temp, candidate)
                    published = True
                    break
                except FileExistsError:
                    if undo_of is not None:
                        raise ValueError("Original path is occupied; undo cancelled")
                    number += 1
            self.update(operation, state="published", signature=json.dumps(signature(candidate)))
            if signature(source) != proposal.signature or self.digest(source, "Final check") != expected:
                raise ValueError("Source changed; both copies retained for review")
            self.finishing(source)
            # ponytail: readiness is heuristic; downloader-specific completion signals if needed.
            source.unlink()
            temp.unlink()
            self.update(operation, state="complete", temp="", signature=json.dumps(signature(candidate)))
            if undo_of is not None:
                self.update(undo_of, state="undone")
            return candidate
        except OperationCancelled as error:
            # Never remove a published file on cancellation: it may have been opened or edited.
            state = "review" if published else "cancelled"
            detail = "Cancelled; both copies retained. Resolve in History." if published else str(error)
            try:
                if temp is not None:
                    safe_path(temp).unlink(missing_ok=True)
                saved = {"signature": json.dumps(signature(candidate))} if published else {}
                self.update(operation, state=state, temp="", error=detail, **saved)
            except (OSError, ValueError) as cleanup_error:
                self.update(operation, state="review", error=f"{detail}; cleanup pending: {cleanup_error}")
            raise OperationCancelled(detail) from error
        except Exception as error:
            self.update(operation, state="review", error=str(error))
            raise

    def undo(self, operation):
        row = self.db.execute("SELECT source,destination,state,hash,signature,undo_of FROM operations WHERE id=?",
                              (operation,)).fetchone()
        if not row or row[2] != "complete" or row[5] is not None:
            raise ValueError("Select a completed move to undo")
        source, destination = Path(row[0]), Path(row[1])
        if source.exists() or source.is_symlink():
            raise ValueError("Original path is occupied; undo cancelled")
        safe_path(destination)
        if not destination.is_file() or tuple(json.loads(row[4])) != signature(destination) or self.digest(destination) != row[3]:
            raise ValueError("Destination changed or is missing; undo cancelled")
        return self.move(Proposal(destination, source, "Undo", signature(destination)), undo_of=operation)

    def resolve_review(self, operation, choice):
        row = self.db.execute("SELECT source,destination,state,hash,signature,temp,undo_of FROM operations WHERE id=?",
                              (operation,)).fetchone()
        if not row or row[2] != "review" or choice not in ("move", "keep"):
            raise ValueError("Select a move marked review")
        source, target = safe_path(row[0]), safe_path(row[1])
        if not source.is_file():
            raise ValueError("Original file is missing; no action taken")
        if target.exists() or target.is_symlink():
            if (not target.is_file() or tuple(json.loads(row[4])) != signature(target)
                    or self.digest(target, "Verifying copy") != row[3] or self.digest(source, "Verifying original") != row[3]):
                raise ValueError("A copy changed; both files were left untouched")
            self.finishing(source)
            if choice == "move":
                source.unlink()
                state = "complete"
            else:
                self.update(operation, state="keep_pending")
                try:
                    target.unlink()
                except OSError as error:
                    self.update(operation, state="review", error=str(error))
                    raise
                state = "kept"
        elif choice == "move":
            self.check_cancel()
            self.update(operation, state="retryable", error="Retry requested from History")
            return self.move(Proposal(source, target, "Review", signature(source)))
        else:
            self.check_cancel()
            state = "kept"
        self.update(operation, state=state, signature=json.dumps(signature(target if state == "complete" else source)),
                    temp="", error="")
        if state == "complete" and row[6] is not None:
            self.update(row[6], state="undone")
        if row[5]:
            partial = Path(row[5])
            if (partial.name.startswith(".organizer-") and partial.suffix == ".tmp"
                    and safe_path(partial).parent == target.parent and partial.is_file()):
                try:
                    partial.unlink()
                except OSError:
                    pass
        return target if state == "complete" else source

    def recover(self, verify=True):
        deferred = False
        rows = self.db.execute("""SELECT id,source,destination,hash,signature,temp,undo_of,error
            FROM operations WHERE state IN ('pending','published','review','keep_pending')""").fetchall()
        for operation, source, destination, expected, saved, temp, undo_of, error in rows:
            try:
                original, target = safe_path(source), safe_path(destination)
                state = self.db.execute("SELECT state FROM operations WHERE id=?", (operation,)).fetchone()[0]
                if state == "keep_pending" and original.is_file() and not target.exists():
                    if temp:
                        partial = Path(temp)
                        if partial.name.startswith(".organizer-") and partial.suffix == ".tmp":
                            partial = safe_path(partial)
                            if partial.parent == target.parent and partial.is_file():
                                partial.unlink()
                    self.update(operation, state="kept", signature=json.dumps(signature(original)),
                                temp="", error="")
                    continue
                if original.is_file() and not target.exists():
                    if temp:
                        partial = Path(temp)
                        if partial.name.startswith(".organizer-") and partial.suffix == ".tmp":
                            partial = safe_path(partial)
                            if partial.parent == target.parent and partial.is_file():
                                partial.unlink()
                    detail = (f"{error or 'Move was interrupted'}; original is intact and "
                              "destination is absent. Refresh Preview to retry.")
                    self.update(operation, state="retryable", error=detail)
                    continue
                if not verify and not original.exists() and target.is_file():
                    deferred = True
                    continue
                if (not original.exists() and not original.is_symlink() and target.is_file()
                        and signature(target)[:4] == tuple(json.loads(saved))[:4] and self.digest(target, "Recovering") == expected):
                    self.update(operation, state="complete", error="")
                    if undo_of is not None:
                        self.update(undo_of, state="undone")
                else:
                    self.update(operation, state="review", error="Interrupted operation: files retained; inspect paths before acting")
            except (OSError, ValueError, TypeError) as error:
                self.update(operation, state="review", error=str(error))
        return deferred
