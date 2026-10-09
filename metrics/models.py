from django.db import models
from django.utils import timezone

from system_monitor import CPU_WARN_THRESHOLD, DISK_ALERT_THRESHOLD, RAM_WARN_THRESHOLD


class ServerMetric(models.Model):
    hostname = models.CharField(max_length=100, default="localhost")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    cpu_percent = models.FloatField()
    ram_percent = models.FloatField()
    disk_percent = models.FloatField()
    log_tail = models.TextField(blank=True)
    simulated = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.hostname} @ {self.created_at:%Y-%m-%d %H:%M:%S}"

    # Soglie "critiche": usate dal template per colorare in rosso
    @property
    def cpu_critical(self) -> bool:
        return self.cpu_percent > CPU_WARN_THRESHOLD

    @property
    def ram_critical(self) -> bool:
        return self.ram_percent > RAM_WARN_THRESHOLD

    @property
    def disk_critical(self) -> bool:
        return self.disk_percent > DISK_ALERT_THRESHOLD

    @property
    def is_critical(self) -> bool:
        return self.cpu_critical or self.ram_critical or self.disk_critical
