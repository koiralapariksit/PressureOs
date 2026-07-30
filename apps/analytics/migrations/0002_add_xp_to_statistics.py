from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="statistics",
            name="xp",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
