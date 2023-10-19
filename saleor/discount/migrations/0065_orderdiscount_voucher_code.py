# Generated by Django 3.2.21 on 2023-10-13 09:59

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("discount", "0064_voucher_single_use"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderdiscount",
            name="voucher_code",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="checkoutlinediscount",
            name="voucher_code",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="orderlinediscount",
            name="voucher_code",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
