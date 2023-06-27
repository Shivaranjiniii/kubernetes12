# Generated by Django 3.2.19 on 2023-06-27 16:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0080_user_customer_group'),
        ('b2b', '0003_auto_20230626_1305'),
    ]

    operations = [
        migrations.AlterField(
            model_name='companyinfo',
            name='customer',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='company', to='account.user'),
        ),
    ]
