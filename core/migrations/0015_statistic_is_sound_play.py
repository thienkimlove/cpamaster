# Generated by Django 2.0.7 on 2018-08-09 14:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_auto_20180809_1347'),
    ]

    operations = [
        migrations.AddField(
            model_name='statistic',
            name='is_sound_play',
            field=models.BooleanField(default=False),
        ),
    ]
