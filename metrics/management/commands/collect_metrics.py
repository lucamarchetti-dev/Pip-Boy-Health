from django.core.management.base import BaseCommand

from metrics.services import collect_and_store


class Command(BaseCommand):
    help = "Raccoglie le metriche di sistema e le salva nel DB (adatto a cron)."

    def add_arguments(self, parser):
        parser.add_argument("--simulate", action="store_true")
        parser.add_argument("--disk", type=float, help="forza la % disco")
        parser.add_argument("--count", type=int, default=1,
                            help="numero di rilevazioni da salvare")

    def handle(self, *args, **opts):
        for _ in range(opts["count"]):
            obj, alerts = collect_and_store(opts["simulate"], opts["disk"])
            self.stdout.write(self.style.SUCCESS(
                f"Salvata: CPU {obj.cpu_percent}% RAM {obj.ram_percent}% "
                f"DISCO {obj.disk_percent}%"))
            for a in alerts:
                self.stdout.write(self.style.ERROR(a))
