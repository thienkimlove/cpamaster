# Generated by Django 2.0.7 on 2018-08-09 10:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_auto_20180808_2203'),
    ]

    operations = [
        migrations.AlterField(
            model_name='offer',
            name='active',
            field=models.BooleanField(default=False),
        ),
    ]
