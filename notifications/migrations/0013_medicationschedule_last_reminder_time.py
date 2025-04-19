# Generated manually

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0012_medicationschedule_duration_days_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicationschedule',
            name='last_reminder_time',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ] 