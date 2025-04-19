from django.db import models

class RecoveryTip(models.Model):
    patient = models.ForeignKey('notifications.Patient', on_delete=models.CASCADE) 
    doctor = models.ForeignKey('notifications.Doctor', on_delete=models.CASCADE)  # ✅ Linked to Doctor
    advice = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tip by Dr. {self.doctor.user.username}: {self.advice[:50]}"
