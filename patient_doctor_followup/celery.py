import os
from celery import Celery
from celery.schedules import crontab

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'patient_doctor_followup.settings')

app = Celery('patient_doctor_followup')

# Load task modules from all registered Django app configs
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Force Celery to use "solo" execution mode
app.conf.worker_pool = 'solo'

app.conf.beat_schedule = {
    'send_appointment_reminders_every_hour': {
        'task': 'notifications.tasks.send_appointment_reminders',
        'schedule': 3600.0,  # Every hour
    },
    'check_vitals_alerts_every_15_minutes': {
        'task': 'notifications.tasks.check_vitals_and_alert',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'check_medication_reminders': {
        'task': 'notifications.tasks.check_and_send_medication_reminders',
        'schedule': 60.0,  # Every minute
    },
}
