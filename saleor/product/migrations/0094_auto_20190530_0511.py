# Generated by Django 2.2.1 on 2019-05-30 10:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0093_auto_20190521_0124'),
    ]

    operations = [
        migrations.CreateModel(
            name='AttributeCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.AddField(
            model_name='attribute',
            name='attribute_category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='product.AttributeCategory'),
        ),
    ]
