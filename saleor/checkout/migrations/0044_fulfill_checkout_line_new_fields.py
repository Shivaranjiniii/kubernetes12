# Generated by Django 3.2.13 on 2022-04-29 08:51

from django.db import migrations
from django.db.models import F, OuterRef, Subquery, Case, When
from django.contrib.postgres.functions import RandomUUID
from django.contrib.postgres.operations import CryptoExtension


def set_checkout_line_token_old_id_and_created_at(apps, _schema_editor):
    CheckoutLine = apps.get_model("checkout", "CheckoutLine")
    Checkout = apps.get_model("checkout", "Checkout")

    CheckoutLine.objects.update(
        old_id=F("id"),
        token=Case(When(token__isnull=True, then=RandomUUID()), default="token"),
        created_at=Case(
            When(
                token__isnull=True,
                then=Subquery(
                    Checkout.objects.filter(lines=OuterRef("id")).values("created_at")[
                        :1
                    ]
                ),
            ),
            default="created_at",
        ),
    )


def set_checkout_line_old_id(apps, schema_editor):
    CheckoutLine = apps.get_model("checkout", "CheckoutLine")
    CheckoutLine.objects.all().update(old_id=F("id"))


class Migration(migrations.Migration):

    dependencies = [
        ("checkout", "0043_add_token_old_id_created_at_to_checkout_line"),
    ]

    operations = [
        CryptoExtension(),
        migrations.RunPython(
            set_checkout_line_token_old_id_and_created_at,
            migrations.RunPython.noop,
        ),
    ]
