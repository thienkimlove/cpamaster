# Generated by Django 2.0.7 on 2018-08-09 11:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_auto_20180809_1046'),
    ]

    operations = [
        migrations.AlterField(
            model_name='offer',
            name='active',
            field=models.BooleanField(default=True),
        ),
    ]
