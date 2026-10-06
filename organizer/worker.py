import threading
import time

from PySide6.QtCore import QThread, Signal

from .core import preview
from .moves import Journal, OperationCancelled


class PendingFiles:
    def __init__(self, stable_seconds=2):
        self.stable_seconds = stable_seconds
        self.observed = {}
        self.backlog = None

    def scan(self, proposals, now):
        current = {p.source: p for p in proposals if p.destination is not None}
        if self.backlog is None:
            self.backlog = set(current)
        self.observed = {path: value for path, value in self.observed.items() if path in current}
        ready = []
        for path, proposal in current.items():
            previous = self.observed.get(path)
            if previous is None or previous[0] != proposal.signature:
                self.observed[path] = (proposal.signature, now)
            elif now - previous[1] >= self.stable_seconds:
                ready.append(proposal)
        return sorted(ready, key=lambda p: (p.source not in self.backlog, p.source.name.casefold()))


class MonitorWorker(QThread):
    report = Signal(str)
    changed = Signal()
    progress = Signal(str, str, object, object)
    idle = Signal()

    def __init__(self, folder, rules, data_dir, parent=None, interval=2, stable_seconds=2):
        super().__init__(parent)
        self.folder, self.rules, self.data_dir = folder, rules, data_dir
        self.interval = interval
        self.pending = PendingFiles(stable_seconds)
        self.wakeup = threading.Event()

    def stop(self):
        self.requestInterruption()
        self.wakeup.set()

    def run(self):
        failed = {}
        try:
            with Journal(self.data_dir / "history.db", cancelled=self.isInterruptionRequested,
                         progress=lambda path, phase, done, total: self.progress.emit(path.name, phase, done, total)) as journal:
                journal.recover()
                self.idle.emit()
                while not self.isInterruptionRequested():
                    self.wakeup.clear()
                    proposals = preview(self.folder, self.rules)
                    ready = self.pending.scan(proposals, time.monotonic())
                    blocked = journal.unresolved_sources()
                    kept = journal.kept_sources()
                    for proposal in ready:
                        if self.isInterruptionRequested():
                            break
                        if (str(proposal.source) in blocked or kept.get(str(proposal.source)) == proposal.signature
                                or failed.get(proposal.source) == proposal.signature):
                            continue
                        try:
                            destination = journal.move(proposal)
                            self.report.emit(f"Moved {proposal.source.name} → {destination}")
                            self.changed.emit()
                        except (OSError, ValueError) as error:
                            failed[proposal.source] = proposal.signature
                            self.report.emit(f"Needs attention: {proposal.source.name}: {error}")
                            self.changed.emit()
                        finally:
                            self.idle.emit()
                    # ponytail: periodic O(files × rules) scan; incremental indexing if folders get large.
                    self.wakeup.wait(self.interval)
        except OperationCancelled as error:
            self.report.emit(str(error))
            self.changed.emit()
        except Exception as error:
            self.report.emit(f"Automatic sorting stopped: {error}")
