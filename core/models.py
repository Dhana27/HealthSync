# core/models.py
from django.db import models
from django.contrib.auth.models import User
from django import forms
from notifications.models import Patient


class PatientRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_records')
    symptoms = models.TextField()
    diagnosis = models.TextField(blank=True, null=True)
    prescription = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Record for {self.patient.user.username} at {self.created_at}"


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.username} to {self.recipient.username} at {self.timestamp}"
    
class FitbitVitals(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Link to a patient
    date = models.DateField()
    resting_heart_rate = models.IntegerField(null=True, blank=True)
    alert_triggered = models.BooleanField(default=False)
    spo2 = models.IntegerField(null=True, blank=True)
    sleep_minutes = models.IntegerField(null=True, blank=True)
    body_temp = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.date} - HR: {self.resting_heart_rate}"

class PatientRegisterForm(forms.ModelForm):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    phone_number = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password']