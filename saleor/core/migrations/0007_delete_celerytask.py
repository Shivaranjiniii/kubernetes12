# Generated by Django 3.2.18 on 2023-04-27 07:56

from django.db import migrations


# No need to seperate state and db, cause CeleryTask model
# was removed from code in previous version
class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_celerytask"),
    ]

    operations = [
        migrations.DeleteModel(
            name="CeleryTask",
        ),
    ]
