from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0013_menu_flow_json"),
    ]

    operations = [
        migrations.AddField(
            model_name="wabaconfig",
            name="flow_enabled",
            field=models.BooleanField(default=False),
        ),
    ]
