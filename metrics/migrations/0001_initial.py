import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ServerMetric",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hostname", models.CharField(default="localhost", max_length=100)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("cpu_percent", models.FloatField()),
                ("ram_percent", models.FloatField()),
                ("disk_percent", models.FloatField()),
                ("log_tail", models.TextField(blank=True)),
                ("simulated", models.BooleanField(default=False)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
