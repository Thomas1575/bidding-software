# Generated by Django 3.2.4 on 2021-06-15 07:35

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=500)),
                ('dt_up', models.DateTimeField(verbose_name='date/time up')),
                ('dt_down', models.DateTimeField(verbose_name='date/time down')),
                ('base_price', models.IntegerField(max_length=0)),
                ('winning_name', models.CharField(max_length=50)),
                ('winning_price', models.IntegerField(max_length=0)),
                ('live', models.BooleanField(default=False)),
                ('closed', models.BooleanField(default=False)),
            ],
        ),
    ]