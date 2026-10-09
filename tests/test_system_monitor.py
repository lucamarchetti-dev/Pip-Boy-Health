import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from system_monitor import SystemMonitor  # noqa: E402


class SystemMonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def make(self, **kw):
        return SystemMonitor(report_dir=self.tmp.name, simulate=True, **kw)

    def test_reports_are_written_and_appended(self):
        m = self.make(forced_disk=50)
        m.run()
        m.run()
        data = json.loads((Path(self.tmp.name) / "metrics.json").read_text())
        self.assertEqual(len(data), 2)
        with open(Path(self.tmp.name) / "metrics.csv") as fh:
            self.assertEqual(len(list(csv.DictReader(fh))), 2)

    def test_no_alert_below_threshold(self):
        _, alerts = self.make(forced_disk=80).run()  # 80 NON supera 80
        self.assertEqual(alerts, [])

    def test_alert_above_threshold(self):
        with mock.patch.object(SystemMonitor, "send_alert") as send:
            _, alerts = self.make(forced_disk=81).run()
        self.assertEqual(len(alerts), 1)
        send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
