# Generated by Django 3.2.18 on 2024-10-27 16:35

from django.apps import apps as registry
from django.db import migrations
from django.db.models.signals import post_migrate

from .tasks.saleor3_19 import (
    update_discount_type_checkout_line_task,
    update_discount_type_order_line_task,
)


def rename_discount_type_promotion_to_catalogue_promotion(_apps, _schema_editor):
    def on_migrations_complete(**_kwargs):
        update_discount_type_checkout_line_task.delay()
        update_discount_type_order_line_task.delay()

    sender = registry.get_app_config("discount")
    post_migrate.connect(on_migrations_complete, weak=False, sender=sender)


class Migration(migrations.Migration):
    dependencies = [
        ("discount", "0084_auto_20241027_2201"),
    ]

    operations = [
        migrations.RunPython(
            rename_discount_type_promotion_to_catalogue_promotion,
            reverse_code=migrations.RunPython.noop,
        )
    ]
