# Generated by Django 3.2.4 on 2021-06-15 11:06

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('bidding', '0008_auto_20210615_1020'),
    ]

    operations = [
        migrations.AddField(
            model_name='bid',
            name='dt_bid',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]