from celery import shared_task
from .models import RecoveryTip
from notifications.models import Patient 
import random

@shared_task
def generate_recovery_tips():
    tips = [
        "Drink at least 2L of water daily.",
        "Take a short walk every 30 minutes.",
        "Eat balanced meals rich in vitamins.",
    ]
    for patient in Patient.objects.all():
        RecoveryTip.objects.create(patient=patient, advice=random.choice(tips))
