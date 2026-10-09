"""Collega la classe SystemMonitor (script) al modello Django."""
import socket

from system_monitor import SystemMonitor

from .models import ServerMetric


def collect_and_store(simulate: bool = False, forced_disk: float | None = None):
    """Rileva le metriche, scrive i report su file, lancia gli alert e salva nel DB."""
    monitor = SystemMonitor(simulate=simulate, forced_disk=forced_disk)
    metrics, alerts = monitor.run()
    obj = ServerMetric.objects.create(
        hostname=socket.gethostname(),
        cpu_percent=metrics.cpu_percent,
        ram_percent=metrics.ram_percent,
        disk_percent=metrics.disk_percent,
        log_tail="\n".join(metrics.log_tail),
        simulated=metrics.simulated,
    )
    return obj, alerts
