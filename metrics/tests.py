from unittest import mock

from django.test import TestCase
from django.urls import reverse

from .models import ServerMetric


class ServerMetricTests(TestCase):
    def test_critical_flags(self):
        m = ServerMetric(cpu_percent=10, ram_percent=10, disk_percent=81)
        self.assertTrue(m.disk_critical)
        self.assertFalse(m.cpu_critical)
        self.assertTrue(m.is_critical)

    def test_not_critical_at_threshold(self):
        m = ServerMetric(cpu_percent=85, ram_percent=85, disk_percent=80)
        self.assertFalse(m.is_critical)


class ViewTests(TestCase):
    def test_dashboard_empty(self):
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_critical_row_is_red(self):
        ServerMetric.objects.create(cpu_percent=1, ram_percent=1, disk_percent=95)
        resp = self.client.get(reverse("dashboard"))
        self.assertContains(resp, 'class="crit"')

    def test_collect_now_creates_row_and_alerts(self):
        with mock.patch("system_monitor.SystemMonitor.send_alert") as send:
            with mock.patch("system_monitor.SystemMonitor.read_disk", return_value=95.0):
                self.client.post(reverse("collect_now"), {"mode": "simulate"})
        self.assertEqual(ServerMetric.objects.count(), 1)
        send.assert_called_once()

    def test_collect_now_ajax_returns_json(self):
        with mock.patch("system_monitor.SystemMonitor.send_alert"):
            with mock.patch("system_monitor.SystemMonitor.read_disk", return_value=95.0):
                resp = self.client.post(
                    reverse("collect_now"), {"mode": "simulate"},
                    HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["critical"])

    def test_api(self):
        ServerMetric.objects.create(cpu_percent=1, ram_percent=1, disk_percent=1)
        data = self.client.get(reverse("api_metrics")).json()
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["total"], 1)
        self.assertIn("disk_critical", data["results"][0])
