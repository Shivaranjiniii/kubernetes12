# Generated by Django 2.0.3 on 2018-07-19 10:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0048_auto_20180629_1055'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ('-pk',), 'permissions': (('manage_orders', 'Manage orders, fulfillments and order notifications.'),)},
        ),
    ]
