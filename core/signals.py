from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from notifications.models import Patient, Doctor

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        if instance.email.endswith("@hospital.com"):  # Example condition
            Doctor.objects.create(user=instance)  # Assign as Doctor
        else:
            Patient.objects.create(user=instance)  # Assign as Patient

post_save.connect(create_profile, sender=User)
