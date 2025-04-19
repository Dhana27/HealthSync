# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0013_medicationschedule_last_reminder_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicationschedule',
            name='reminder_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('sent', 'Reminder Sent'),
                    ('overdue', 'Overdue Reminder Sent'),
                    ('taken', 'Medication Taken'),
                    ('missed', 'Medication Missed')
                ],
                default='pending',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='medicationschedule',
            name='taken_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ] 