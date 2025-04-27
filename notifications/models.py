from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from celery import shared_task
from datetime import datetime
from django.utils.timezone import make_aware
import pytz
from django.utils import timezone

# doctor model
class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialty = models.CharField(max_length=255)
    is_available_for_call = models.BooleanField(default=False)
    role = models.CharField(max_length=10, choices=[('doctor', 'Doctor')], default='doctor')

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username} ({self.specialty})"

# patient model 
class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    assigned_doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    caregiver_phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField()
    role = models.CharField(max_length=10, choices=[('patient', 'Patient')], default='patient')
    fitbit_access_token = models.TextField(null=True, blank=True)
    fitbit_refresh_token = models.TextField(null=True, blank=True)
    fitbit_connected = models.BooleanField(default=False)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class ConsultRequest(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consult_requests')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_requests')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed')
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    room_url = models.URLField(null=True, blank=True)  # filled when accepted
    room_id = models.CharField(max_length=100, blank=True, null=True)
    prescription = models.OneToOneField('Prescription', null=True, blank=True, on_delete=models.SET_NULL)
    viewed_by_doctor = models.BooleanField(default=False)


# track medication prescribed and scheduled
class MedicationSchedule(models.Model):
    patient = models.ForeignKey('notifications.Patient', on_delete=models.CASCADE, related_name="medications")
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=255)
    time = models.TimeField()
    date = models.DateField(default=now)
    duration_days = models.PositiveIntegerField(default=1)  # Number of days to take medication
    food_timing = models.CharField(max_length=50, choices=[
        ('before', 'Before Food'),
        ('after', 'After Food'),
        ('with', 'With Food')
    ], default='after')
    reminder_sent = models.BooleanField(default=False)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('taken', 'Taken'),
        ('overdue', 'Overdue'),
        ('missed', 'Missed'),
        ('ended', 'Ended')
    ]
    reminder_status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    last_status_date = models.DateField(default=timezone.now)
    taken_time = models.DateTimeField(null=True, blank=True)  # When the patient marked it as taken
    end_date = models.DateField(null=True, blank=True)  # Calculated based on start date + duration

    def save(self, *args, **kwargs):
        if self.date and self.duration_days:
            from datetime import timedelta
            self.end_date = self.date + timedelta(days=self.duration_days - 1)  # -1 because start date counts as day 1
        super().save(*args, **kwargs)

    def mark_as_taken(self):
        """Mark the medication as taken"""
        self.reminder_status = 'taken'
        self.taken_time = timezone.now()
        self.save()

    def reset_for_next_day(self):
        """Reset the reminder status for the next day"""
        self.reminder_status = 'pending'
        self.reminder_sent = False
        self.last_status_date = timezone.now()
        self.taken_time = None
        self.save()

    def schedule_sms_reminder(self):
        """Schedule SMS reminders for each day of the medication duration"""
        from notifications.tasks import send_sms_reminder
        from datetime import datetime, timedelta
        
        # Set to Singapore timezone
        singapore_tz = pytz.timezone("Asia/Singapore")
        
        # Schedule reminders for each day
        for day in range(self.duration_days):
            reminder_date = self.date + timedelta(days=day)
            schedule_dt = datetime.combine(reminder_date, self.time)
            aware_dt = make_aware(schedule_dt, timezone=singapore_tz)
            
            # Create reminder message
            message = (
                f"Time to take {self.medication_name} ({self.dosage}) - {self.get_food_timing_display()}. "
                f"Day {day + 1} of {self.duration_days}"
            )
            
            # Send task to Celery with the specific message
            send_sms_reminder.apply_async(
                args=(self.id, message),
                eta=aware_dt
            )

    def __str__(self):
        return f"{self.medication_name} - {self.dosage} ({self.date} to {self.end_date})"

# doctor appointment 
class Appointment(models.Model):
    patient = models.ForeignKey('notifications.Patient', on_delete=models.CASCADE)
    doctor = models.ForeignKey('notifications.Doctor', on_delete=models.CASCADE)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    reminder_sent = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Appointment with {self.doctor.user.username if self.doctor.user else 'Unknown Doctor'} on {self.appointment_date} at {self.appointment_time}"

class Prescription(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="prescriptions")
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="patient_prescriptions")
    diagnosis = models.TextField()
    advice = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Medication(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='medications')
    name = models.CharField(max_length=255)
    food_timing = models.CharField(max_length=50)  # e.g., 'Before Food' / 'After Food'
    times_per_day = models.PositiveIntegerField()

class MedicalHistory(models.Model):
    patient = models.ForeignKey('notifications.Patient', on_delete=models.CASCADE, related_name='medical_history')
    doctor = models.ForeignKey('notifications.Doctor', on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()
    diagnosis = models.TextField()
    symptoms = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Medical History for {self.patient.user.get_full_name()} on {self.date}"

class MedicalHistoryMedication(models.Model):
    medical_history = models.ForeignKey(MedicalHistory, on_delete=models.CASCADE, related_name='medications')
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=255)
    duration_days = models.PositiveIntegerField()
    food_timing = models.CharField(max_length=50, choices=[
        ('before', 'Before Food'),
        ('after', 'After Food'),
        ('with', 'With Food')
    ])

    def __str__(self):
        return f"{self.medication_name} - {self.dosage}"

class PatientFeedback(models.Model):
    SEVERITY_CHOICES = [
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ]
    
    URGENCY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]
    
    patient = models.ForeignKey(User, on_delete=models.CASCADE)
    feedback_text = models.TextField()
    pain_level = models.IntegerField(help_text="Pain level from 0-10", null=True, blank=True)
    sentiment_label = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, default='neutral')
    severity_level = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='mild')
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='low')
    follow_up_needed = models.BooleanField(default=False)
    reasoning = models.TextField(default='No specific reasoning provided')
    consultation_recommended = models.BooleanField(default=False)
    consultation_accepted = models.BooleanField(null=True, blank=True)
    doctor_notes = models.TextField(blank=True, null=True)
    next_steps = models.TextField(blank=True, null=True)
    viewed_by_doctor = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Health Feedback from {self.patient.get_full_name()} - {self.created_at}"
