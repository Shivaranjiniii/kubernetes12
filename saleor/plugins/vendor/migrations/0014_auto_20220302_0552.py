# Generated by Django 3.2.10 on 2022-03-02 05:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vendor", "0013_alter_vendor_is_active"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="vendor",
            name="commercial_info",
        ),
        migrations.AddField(
            model_name="vendor",
            name="registration_type",
            field=models.IntegerField(
                choices=[(1, "Company"), (2, "Maroof")], default=1
            ),
        ),
    ]
