from django.contrib import admin

from .models import ServerMetric


@admin.register(ServerMetric)
class ServerMetricAdmin(admin.ModelAdmin):
    list_display = ("hostname", "created_at", "cpu_percent", "ram_percent",
                    "disk_percent", "simulated")
    list_filter = ("hostname", "simulated")
