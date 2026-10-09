from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from system_monitor import CPU_WARN_THRESHOLD, DISK_ALERT_THRESHOLD, RAM_WARN_THRESHOLD

from .models import ServerMetric
from .services import collect_and_store

LATEST = 20


def dashboard(request):
    rows = list(ServerMetric.objects.all()[:LATEST])
    return render(request, "metrics/dashboard.html", {
        "rows": rows,
        "latest": rows[0] if rows else None,
        "cpu_th": CPU_WARN_THRESHOLD,
        "ram_th": RAM_WARN_THRESHOLD,
        "disk_th": DISK_ALERT_THRESHOLD,
        "latest_count": LATEST,
    })


@require_POST
def collect_now(request):
    obj, alerts = collect_and_store(simulate=request.POST.get("mode") == "simulate")
    # Chiamata da JavaScript (senza ricaricare la pagina) -> risposta JSON
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "ok": True,
            "critical": obj.is_critical,
            "disk_percent": obj.disk_percent,
            "alerts": alerts,
        })
    return redirect("dashboard")


def api_metrics(request):
    data = [
        {
            "id": m.id,
            "hostname": m.hostname,
            "created_at": m.created_at.isoformat(),
            "cpu_percent": m.cpu_percent,
            "ram_percent": m.ram_percent,
            "disk_percent": m.disk_percent,
            "cpu_critical": m.cpu_critical,
            "ram_critical": m.ram_critical,
            "disk_critical": m.disk_critical,
            "critical": m.is_critical,
            "simulated": m.simulated,
            "log_tail": m.log_tail,
        }
        for m in ServerMetric.objects.all()[:LATEST]
    ]
    return JsonResponse({"results": data, "total": ServerMetric.objects.count()})
