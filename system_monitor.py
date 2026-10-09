#!/usr/bin/env python3
"""
system_monitor.py - Classe SystemMonitor (parte "Script & OOP").

Legge (o simula) le metriche di sistema: CPU, RAM, disco e ultime righe di log.
Salva i dati in reports/metrics.json e reports/metrics.csv e solleva un alert
se l'uso del disco supera la soglia (default 80%).

Alert supportati (tutti opzionali, combinabili):
  - log su file/console (sempre attivo)
  - Telegram  -> variabili d'ambiente TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID
  - Webhook   -> variabile d'ambiente ALERT_WEBHOOK_URL (POST JSON)

Uso:
    python system_monitor.py                 # rilevazione reale (psutil se presente)
    python system_monitor.py --simulate      # valori casuali, utile per i test
    python system_monitor.py --simulate --disk 92   # forza un disco al 92%
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import random
import shutil
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:  # psutil è opzionale: senza, si usano fallback stdlib o simulazione
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_REPORT_DIR = BASE_DIR / "reports"

DISK_ALERT_THRESHOLD = 80.0   # %
CPU_WARN_THRESHOLD = 85.0     # % (usati anche dalla dashboard)
RAM_WARN_THRESHOLD = 85.0     # %

logger = logging.getLogger("system_monitor")


@dataclass
class Metrics:
    """Istantanea delle metriche di sistema."""
    timestamp: str
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    log_tail: list[str] = field(default_factory=list)
    simulated: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class SystemMonitor:
    CSV_FIELDS = ["timestamp", "cpu_percent", "ram_percent",
                  "disk_percent", "simulated", "log_tail"]

    def __init__(
        self,
        report_dir: str | Path = DEFAULT_REPORT_DIR,
        disk_path: str = "/",
        disk_threshold: float = DISK_ALERT_THRESHOLD,
        log_file: str | None = "/var/log/syslog",
        log_lines: int = 5,
        simulate: bool = False,
        forced_disk: float | None = None,
    ):
        self.report_dir = Path(report_dir)
        self.disk_path = disk_path
        self.disk_threshold = disk_threshold
        self.log_file = log_file
        self.log_lines = log_lines
        self.simulate = simulate
        self.forced_disk = forced_disk
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()

    # ------------------------------------------------------------------ logging
    def _setup_logging(self) -> None:
        if logger.handlers:
            return
        logger.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        logger.addHandler(console)
        try:
            fh = logging.FileHandler(self.report_dir / "alerts.log", encoding="utf-8")
            fh.setFormatter(fmt)
            logger.addHandler(fh)
        except OSError:  # pragma: no cover
            pass

    # ------------------------------------------------------------------ lettura
    def read_cpu(self) -> float:
        if self.simulate:
            return round(random.uniform(5, 95), 1)
        if psutil:
            return float(psutil.cpu_percent(interval=0.5))
        if hasattr(os, "getloadavg"):  # fallback Linux/macOS: load average normalizzato
            load1, _, _ = os.getloadavg()
            return round(min(100.0, load1 / (os.cpu_count() or 1) * 100), 1)
        logger.warning("psutil non installato: CPU non rilevabile su questo sistema (pip install psutil)")
        return 0.0

    def read_ram(self) -> float:
        if self.simulate:
            return round(random.uniform(20, 95), 1)
        if psutil:
            return float(psutil.virtual_memory().percent)
        return self._ram_from_proc_meminfo()

    @staticmethod
    def _ram_from_proc_meminfo() -> float:
        info: dict[str, int] = {}
        try:
            with open("/proc/meminfo", encoding="utf-8") as fh:
                for line in fh:
                    key, value = line.split(":", 1)
                    info[key] = int(value.split()[0])
            total, avail = info["MemTotal"], info["MemAvailable"]
            return round((total - avail) / total * 100, 1)
        except (OSError, KeyError, ValueError):
            return 0.0

    def read_disk(self) -> float:
        if self.forced_disk is not None:
            return float(self.forced_disk)
        if self.simulate:
            return round(random.uniform(30, 98), 1)
        usage = shutil.disk_usage(self.disk_path)
        return round(usage.used / usage.total * 100, 1)

    def read_logs(self) -> list[str]:
        """Ultime N righe del log di sistema; se non leggibile, righe simulate."""
        if not self.simulate and self.log_file:
            try:
                with open(self.log_file, encoding="utf-8", errors="replace") as fh:
                    return [l.rstrip() for l in fh.readlines()[-self.log_lines:]]
            except OSError:
                pass  # permessi/assenza file -> fallback
        samples = [
            "kernel: eth0 link is up",
            "sshd[1021]: Accepted publickey for admin",
            "cron[882]: (root) CMD (/usr/local/bin/backup.sh)",
            "systemd[1]: Started Daily apt download activities",
            "nginx[1450]: worker process started",
            "kernel: Out of memory: killed process 3321",
        ]
        return random.sample(samples, k=min(self.log_lines, len(samples)))

    # ------------------------------------------------------------------ raccolta
    def collect(self) -> Metrics:
        return Metrics(
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            cpu_percent=self.read_cpu(),
            ram_percent=self.read_ram(),
            disk_percent=self.read_disk(),
            log_tail=self.read_logs(),
            simulated=self.simulate,
        )

    # ------------------------------------------------------------------ report
    def save_json(self, metrics: Metrics, filename: str = "metrics.json") -> Path:
        """Accoda la rilevazione a una lista JSON (il file resta valido)."""
        path = self.report_dir / filename
        data: list[dict] = []
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("%s corrotto: lo ricreo", path.name)
        data.append(metrics.to_dict())
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def save_csv(self, metrics: Metrics, filename: str = "metrics.csv") -> Path:
        path = self.report_dir / filename
        new_file = not path.exists()
        with open(path, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=self.CSV_FIELDS)
            if new_file:
                writer.writeheader()
            row = metrics.to_dict()
            row["log_tail"] = " | ".join(row["log_tail"])
            writer.writerow(row)
        return path

    # ------------------------------------------------------------------ alert
    def check_alerts(self, metrics: Metrics) -> list[str]:
        alerts: list[str] = []
        if metrics.disk_percent > self.disk_threshold:
            alerts.append(
                f"DISCO CRITICO: {metrics.disk_percent}% "
                f"(soglia {self.disk_threshold}%) - {metrics.timestamp}"
            )
        for msg in alerts:
            self.send_alert(msg)
        return alerts

    def send_alert(self, message: str) -> None:
        logger.warning(message)
        self._send_telegram(message)
        self._send_webhook(message)

    @staticmethod
    def _post(url: str, payload: dict) -> None:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5):
                pass
        except (urllib.error.URLError, OSError) as exc:
            logger.error("Invio alert fallito (%s): %s", url.split("?")[0], exc)

    def _send_telegram(self, message: str) -> None:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if token and chat_id:
            self._post(f"https://api.telegram.org/bot{token}/sendMessage",
                       {"chat_id": chat_id, "text": message})

    def _send_webhook(self, message: str) -> None:
        url = os.getenv("ALERT_WEBHOOK_URL")
        if url:
            self._post(url, {"text": message})

    # ------------------------------------------------------------------ run
    def run(self) -> tuple[Metrics, list[str]]:
        metrics = self.collect()
        self.save_json(metrics)
        self.save_csv(metrics)
        alerts = self.check_alerts(metrics)
        logger.info("CPU %.1f%% | RAM %.1f%% | DISCO %.1f%%",
                    metrics.cpu_percent, metrics.ram_percent, metrics.disk_percent)
        return metrics, alerts


def main() -> None:
    p = argparse.ArgumentParser(description="System Health Monitor")
    p.add_argument("--simulate", action="store_true", help="usa valori simulati")
    p.add_argument("--disk", type=float, help="forza la percentuale disco")
    p.add_argument("--threshold", type=float, default=DISK_ALERT_THRESHOLD)
    p.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = p.parse_args()
    SystemMonitor(report_dir=args.report_dir, simulate=args.simulate,
                  forced_disk=args.disk, disk_threshold=args.threshold).run()


if __name__ == "__main__":
    main()
