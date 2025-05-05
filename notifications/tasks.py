from celery import shared_task
from twilio.rest import Client
from django.conf import settings
from .models import MedicationSchedule, Appointment, Patient
from datetime import datetime, timedelta
from django.utils import timezone
from core.models import FitbitVitals
from django.contrib.auth.models import User
import pytz
import time
from django.db.models import Q

@shared_task
def send_sms_reminder(medication_id, message=None):
    """Send SMS reminder for a medication"""
    try:
        # Fetch medication details
        medication = MedicationSchedule.objects.get(id=medication_id)
        patient_phone = medication.patient.phone_number
        caregiver_phone = medication.patient.caregiver_phone  # Optional

        if not patient_phone and not caregiver_phone:
            return "Error sending SMS: No phone numbers available"

        # Twilio API Setup
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        if message is None:
            message = f"Reminder: Take your medication '{medication.medication_name}' ({medication.dosage}) - {medication.get_food_timing_display()}"

        sms_sent = False
        # Send SMS to patient
        if patient_phone:
            try:
                client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=patient_phone
                )
                sms_sent = True
            except Exception as e:
                print(f"Error sending SMS to patient: {str(e)}")

        # Send SMS to caregiver (optional)
        if caregiver_phone:
            try:
                client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=caregiver_phone
                )
                sms_sent = True
            except Exception as e:
                print(f"Error sending SMS to caregiver: {str(e)}")

        if not sms_sent:
            return "Error sending SMS: Failed to send to any recipients"

        return f"SMS sent for Medication ID: {medication_id}"

    except Exception as e:
        return f"Error sending SMS: {str(e)}"


@shared_task
def send_appointment_reminders():
    """Send SMS reminders 24 hours before an appointment."""
    now = timezone.now()
    
    # Get appointments in the next 24-25 hours that haven't been reminded
    start_reminder = now + timezone.timedelta(hours=23)  # Start checking from 23 hours ahead
    end_reminder = now + timezone.timedelta(hours=25)    # Until 25 hours ahead
    
    # Find appointments within this window
    appointments = Appointment.objects.filter(
        appointment_date__gte=start_reminder.date(),
        appointment_date__lte=end_reminder.date(),
        reminder_sent=False
    ).select_related('doctor', 'patient')

    if not appointments:
        return "No appointment reminders to send."

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    reminders_sent = 0

    for appointment in appointments:
        # Create appointment datetime for comparison
        appt_datetime = timezone.make_aware(
            datetime.combine(appointment.appointment_date, appointment.appointment_time)
        )
        
        # Only send if appointment is between 23-25 hours away
        if start_reminder <= appt_datetime <= end_reminder:
            patient_phone = appointment.patient.phone_number
            message_body = (
                f"Reminder: You have an appointment with {appointment.doctor} tomorrow "
                f"on {appointment.appointment_date.strftime('%B %d, %Y')} at "
                f"{appointment.appointment_time.strftime('%I:%M %p')}. Please be on time."
            )

            try:
                if patient_phone:
                    client.messages.create(
                        body=message_body,
                        from_=settings.TWILIO_PHONE_NUMBER,
                        to=patient_phone
                    )
                    appointment.reminder_sent = True
                    appointment.save()
                    reminders_sent += 1
            except Exception as e:
                print(f"Failed to send appointment reminder: {e}")

    return f"Successfully sent {reminders_sent} appointment reminder(s)."

@shared_task
def check_vitals_and_alert():
    """Check latest vitals and trigger SMS alerts if values are abnormal"""
    

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    today = timezone.now().date()

    vitals_today = FitbitVitals.objects.filter(date=today)

    alerts_sent = 0

    for vitals in vitals_today:
        user = vitals.user
        patient = Patient.objects.get(user=user)

        # --- Vital sign validation ---
        # Define physiological plausible ranges
        HR_MIN, HR_MAX = 30, 220
        SPO2_MIN, SPO2_MAX = 70, 100
        TEMP_MIN, TEMP_MAX = 93.0, 108.0

        # Track if any value was out of range
        rubbish_data = False
        warning_msgs = []

        # Heart Rate
        if vitals.resting_heart_rate is not None:
            if vitals.resting_heart_rate < HR_MIN:
                warning_msgs.append(f"Heart rate {vitals.resting_heart_rate} too low, set to {HR_MIN}")
                vitals.resting_heart_rate = HR_MIN
                rubbish_data = True
            elif vitals.resting_heart_rate > HR_MAX:
                warning_msgs.append(f"Heart rate {vitals.resting_heart_rate} too high, set to {HR_MAX}")
                vitals.resting_heart_rate = HR_MAX
                rubbish_data = True

        # SpO2
        if vitals.spo2 is not None:
            if vitals.spo2 < SPO2_MIN:
                warning_msgs.append(f"SpO2 {vitals.spo2} too low, set to {SPO2_MIN}")
                vitals.spo2 = SPO2_MIN
                rubbish_data = True
            elif vitals.spo2 > SPO2_MAX:
                warning_msgs.append(f"SpO2 {vitals.spo2} too high, set to {SPO2_MAX}")
                vitals.spo2 = SPO2_MAX
                rubbish_data = True

        # Body Temp
        if vitals.body_temp is not None:
            if vitals.body_temp < TEMP_MIN:
                warning_msgs.append(f"Body temp {vitals.body_temp} too low, set to {TEMP_MIN}")
                vitals.body_temp = TEMP_MIN
                rubbish_data = True
            elif vitals.body_temp > TEMP_MAX:
                warning_msgs.append(f"Body temp {vitals.body_temp} too high, set to {TEMP_MAX}")
                vitals.body_temp = TEMP_MAX
                rubbish_data = True

        if rubbish_data:
            print(f"[INTERNAL WARNING] Rubbish data detected for user {user.username}: " + "; ".join(warning_msgs))
            # Omit from alerting/analysis
            continue

        # Alert logic
        hr_alert = vitals.resting_heart_rate and (vitals.resting_heart_rate < 50 or vitals.resting_heart_rate > 130)
        spo2_alert = vitals.spo2 and vitals.spo2 < 92
        temp_alert = vitals.body_temp and (vitals.body_temp < 96.0 or vitals.body_temp > 100.4)

        if hr_alert or spo2_alert or temp_alert:
            vitals.alert_triggered = True
            vitals.save()

            message_body = (
                f"Health Alert for {user.get_full_name()}:\n"
                f"Heart Rate: {vitals.resting_heart_rate} bpm\n"
                f"SpO2: {vitals.spo2}%\n"
                f"Temp: {vitals.body_temp}°F"
            )

            if patient.phone_number:
                try:
                    client.messages.create(
                        body=message_body,
                        from_=settings.TWILIO_PHONE_NUMBER,
                        to=patient.phone_number
                    )
                except Exception as e:
                    print(f"Error sending SMS to patient {user.username}: {e}")

            if patient.caregiver_phone:
                try:
                    client.messages.create(
                        body=message_body,
                        from_=settings.TWILIO_PHONE_NUMBER,
                        to=patient.caregiver_phone
                    )
                except Exception as e:
                    print(f"Error sending SMS to caregiver of {user.username}: {e}")

            alerts_sent += 1

    return f"{alerts_sent} vitals alert(s) sent."

@shared_task
def check_and_send_medication_reminders():
    """Check for upcoming medication reminders and send them"""
    try:
        # Set to Singapore timezone consistently
        sg_tz = pytz.timezone("Asia/Singapore")
        current_time = timezone.now().astimezone(sg_tz)
        
        print(f"[DEBUG] Current time: {current_time}")

        # Clean up old records (older than 10 days)
        ten_days_ago = current_time.date() - timedelta(days=10)
        MedicationSchedule.objects.filter(end_date__lt=ten_days_ago).delete()
        print("[DEBUG] Cleaned up medications older than 10 days")

        # Reset medications at midnight
        if current_time.hour == 0 and current_time.minute < 5:
            print("[DEBUG] Midnight reset of medication statuses")
            # Mark untaken medications as missed
            MedicationSchedule.objects.filter(
                date__lte=current_time.date(),
                end_date__gte=current_time.date(),
                reminder_status__in=['pending', 'sent', 'overdue']
            ).update(reminder_status='missed')
            
            # Reset today's medications
            MedicationSchedule.objects.filter(
                date__lte=current_time.date(),
                end_date__gte=current_time.date()
            ).update(reminder_status='pending', reminder_sent=False)

        # Find active medications for today that haven't been taken or already reminded
        medications = MedicationSchedule.objects.filter(
            date__lte=current_time.date(),
            end_date__gte=current_time.date(),
            reminder_status='pending'  # Only get pending medications
        )

        print(f"[DEBUG] Found {medications.count()} active medications for today")

        # Process each medication
        medications_to_remind = []
        for med in medications:
            med_time = med.time
            print(f"[DEBUG] Checking medication: {med.medication_name} scheduled for {med_time}")

            # Calculate minutes until/since medication time
            med_datetime = timezone.make_aware(datetime.combine(current_time.date(), med_time), sg_tz)
            time_diff = med_datetime - current_time
            minutes_until = time_diff.total_seconds() / 60

            # Adjust for passed medications (will show as large positive number)
            if minutes_until > 720:  # If more than 12 hours in future
                minutes_until -= 1440  # Subtract 24 hours worth of minutes

            print(f"[DEBUG] Minutes until {med.medication_name}: {minutes_until}")

            # Only send reminder if:
            # 1. Medication is due within next 5 minutes
            # 2. No reminder has been sent today
            if 0 <= minutes_until <= 5 and not med.reminder_sent:
                print(f"[DEBUG] Adding {med.medication_name} to reminder list")
                medications_to_remind.append((med, minutes_until))

        print(f"[DEBUG] Sending reminders for {len(medications_to_remind)} medications")

        # Send reminders
        for medication, minutes_until in medications_to_remind:
            try:
                message = (
                    f"Medication Reminder: Time to take {medication.medication_name} "
                    f"({medication.dosage}) - {medication.get_food_timing_display()}"
                )
                
                # Send the reminder
                send_sms_reminder.apply_async(
                    args=(medication.id, message),
                    retry=True,
                    retry_policy={
                        'max_retries': 3,
                        'interval_start': 0,
                        'interval_step': 0.2,
                        'interval_max': 0.2,
                    }
                )
                # Mark as sent
                medication.reminder_status = 'sent'
                medication.reminder_sent = True
                medication.last_reminder_time = current_time
                medication.save()
            except Exception as e:
                print(f"[ERROR] Failed to send reminder for {medication.medication_name}: {str(e)}")

        # Update status of medications that are overdue
        MedicationSchedule.objects.filter(
            date__lte=current_time.date(),
            end_date__gte=current_time.date(),
            reminder_status='sent',
            time__lt=current_time.time()
        ).update(reminder_status='overdue')

        return f"Processed {len(medications_to_remind)} medication reminders"
    except Exception as e:
        print(f"[ERROR] Error in medication reminder check: {str(e)}")
        return f"Error processing medication reminders: {str(e)}"

