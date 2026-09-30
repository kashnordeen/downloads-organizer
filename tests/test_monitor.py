import unittest
from pathlib import Path

from organizer.core import Proposal
from organizer.worker import PendingFiles


def proposal(name, signature=(1, 2, 3, 4, 5)):
    return Proposal(Path(name), Path("sorted") / name, "Rule", signature)


class MonitorTests(unittest.TestCase):
    def test_backlog_precedes_new_and_duplicates_are_removed(self):
        queue = PendingFiles(stable_seconds=2)
        old = proposal("old.pdf")
        new = proposal("new.pdf")
        self.assertEqual(queue.scan([old, old], 0), [])
        self.assertEqual(queue.scan([new, old, old], 1), [])
        self.assertEqual([p.source.name for p in queue.scan([new, old], 3)], ["old.pdf", "new.pdf"])

    def test_changing_backlog_does_not_starve_ready_new_file(self):
        queue = PendingFiles(stable_seconds=2)
        old, new = proposal("old.pdf"), proposal("new.pdf")
        queue.scan([old], 0)
        queue.scan([old, new], 1)
        changing = proposal("old.pdf", (1, 2, 99, 4, 5))
        self.assertEqual([p.source.name for p in queue.scan([changing, new], 3)], ["new.pdf"])

    def test_disappeared_and_changed_files_are_reobserved(self):
        queue = PendingFiles(stable_seconds=2)
        old = proposal("old.pdf")
        queue.scan([old], 0)
        queue.scan([], 1)
        self.assertEqual(queue.scan([old], 3), [])
        self.assertEqual(queue.scan([old], 5), [old])
