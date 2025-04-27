from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta, time
from .models import MedicationSchedule, Patient, Doctor, User, PatientFeedback
from .tasks import send_sms_reminder, check_and_send_medication_reminders
from .token_utils import generate_token_for_user
import jwt
from django.conf import settings
import pytz
from unittest.mock import patch, Mock

class MedicationScheduleTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create test doctor
        self.doctor = Doctor.objects.create(
            user=self.user,
            specialty='General Medicine'
        )
        
        # Create test patient
        self.patient = Patient.objects.create(
            user=self.user,
            assigned_doctor=self.doctor,
            phone_number='+15555555555'  # Valid Twilio test number
        )

    def test_medication_schedule_end_date_calculation(self):
        """Test that end_date is correctly calculated when saving MedicationSchedule"""
        start_date = timezone.now().date()
        schedule = MedicationSchedule.objects.create(
            patient=self.patient,
            medication_name='Test Med',
            dosage='1 tablet',
            time=timezone.now().time(),
            date=start_date,
            duration_days=5
        )
        
        expected_end_date = start_date + timedelta(days=4)  # -1 because start date counts as day 1
        self.assertEqual(schedule.end_date, expected_end_date)

    def test_medication_mark_as_taken(self):
        """Test marking medication as taken"""
        schedule = MedicationSchedule.objects.create(
            patient=self.patient,
            medication_name='Test Med',
            dosage='1 tablet',
            time=timezone.now().time(),
            date=timezone.now().date()
        )
        
        schedule.mark_as_taken()
        self.assertEqual(schedule.reminder_status, 'taken')
        self.assertIsNotNone(schedule.taken_time)

    def test_medication_reset_for_next_day(self):
        """Test resetting medication status for next day"""
        schedule = MedicationSchedule.objects.create(
            patient=self.patient,
            medication_name='Test Med',
            dosage='1 tablet',
            time=timezone.now().time(),
            date=timezone.now().date(),
            reminder_status='taken',
            reminder_sent=True
        )
        
        schedule.reset_for_next_day()
        self.assertEqual(schedule.reminder_status, 'pending')
        self.assertFalse(schedule.reminder_sent)
        self.assertIsNone(schedule.taken_time)

class TaskTests(TestCase):
    def setUp(self):
        # Create test user and patient
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            user=self.user,
            phone_number='+15555555555'  # Valid Twilio test number
        )

    @patch('notifications.tasks.Client')
    def test_send_sms_reminder_with_phone(self, mock_twilio):
        """Test sending SMS reminder when phone number is present"""
        # Mock Twilio client
        mock_client = mock_twilio.return_value
        mock_client.messages.create.return_value = Mock(sid='test_sid')

        schedule = MedicationSchedule.objects.create(
            patient=self.patient,
            medication_name='Test Med',
            dosage='1 tablet',
            time=time(10, 0),  # Use fixed time 10:00
            date=timezone.now().date()
        )
        
        result = send_sms_reminder(schedule.id)
        self.assertIn("SMS sent for Medication ID", result)
        mock_client.messages.create.assert_called_once()

    def test_send_sms_reminder_without_phone(self):
        """Test sending SMS reminder when phone number is missing"""
        self.patient.phone_number = None
        self.patient.save()
        
        schedule = MedicationSchedule.objects.create(
            patient=self.patient,
            medication_name='Test Med',
            dosage='1 tablet',
            time=time(10, 0),  # Use fixed time 10:00
            date=timezone.now().date()
        )
        
        result = send_sms_reminder(schedule.id)
        self.assertIn("Error sending SMS", result)

    @patch('django.utils.timezone.now')
    def test_check_and_send_medication_reminders(self, mock_now):
        """Test the medication reminder checking and sending process"""
        # Set up mock time in Singapore timezone
        sg_tz = pytz.timezone('Asia/Singapore')
        fixed_now = datetime(2024, 1, 1, 10, 0).replace(tzinfo=sg_tz)
        mock_now.return_value = fixed_now
        
        # Create medication due in next 5 minutes
        med_time = time(10, 2)  # 10:02, 2 minutes after current time
        
        schedule = MedicationSchedule.objects.create(
            patient=self.patient,
            medication_name='Test Med',
            dosage='1 tablet',
            time=med_time,
            date=fixed_now.date(),
            reminder_status='pending',
            reminder_sent=False
        )
        
        # Mock Twilio client
        with patch('notifications.tasks.Client') as mock_twilio:
            mock_client = mock_twilio.return_value
            mock_client.messages.create.return_value = Mock(sid='test_sid')
            
            # Mock the send_sms_reminder task
            with patch('notifications.tasks.send_sms_reminder.apply_async') as mock_send_reminder:
                mock_send_reminder.return_value = True
                
                result = check_and_send_medication_reminders()
                
                # Refresh schedule from database
                schedule.refresh_from_db()
                self.assertEqual(schedule.reminder_status, 'sent')
                self.assertTrue(schedule.reminder_sent)
                mock_send_reminder.assert_called_once()

class TokenUtilsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_generate_token_for_user(self):
        """Test JWT token generation and validation"""
        role = 'doctor'
        token = generate_token_for_user(self.user, role)
        
        # Verify token can be decoded
        decoded = jwt.decode(token, settings.HMS_SECRET, algorithms=["HS256"])
        
        # Check token payload
        self.assertEqual(decoded['user_id'], str(self.user.id))
        self.assertEqual(decoded['role'], role)
        self.assertEqual(decoded['type'], 'room-code')
        self.assertEqual(decoded['version'], 2)
        self.assertIn('iat', decoded)
        self.assertIn('exp', decoded)

class PatientFeedbackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.doctor = Doctor.objects.create(
            user=self.user,
            specialty='General Medicine'
        )
        self.patient = Patient.objects.create(
            user=self.user,
            assigned_doctor=self.doctor
        )

    def test_feedback_creation(self):
        """Test creating patient feedback with all fields"""
        feedback = PatientFeedback.objects.create(
            patient=self.user,
            feedback_text='Test feedback',
            pain_level=5,
            sentiment_label='neutral',
            severity_level='moderate',
            urgency='medium',
            follow_up_needed=True,
            reasoning='Test reasoning',
            consultation_recommended=True
        )
        
        self.assertEqual(feedback.feedback_text, 'Test feedback')
        self.assertEqual(feedback.pain_level, 5)
        self.assertEqual(feedback.severity_level, 'moderate')
        self.assertEqual(feedback.urgency, 'medium')
        self.assertTrue(feedback.follow_up_needed)
        self.assertTrue(feedback.consultation_recommended)
        self.assertFalse(feedback.viewed_by_doctor)

    def test_feedback_viewed_by_doctor(self):
        """Test marking feedback as viewed by doctor"""
        feedback = PatientFeedback.objects.create(
            patient=self.user,
            feedback_text='Test feedback'
        )
        
        feedback.viewed_by_doctor = True
        feedback.save()
        
        updated_feedback = PatientFeedback.objects.get(id=feedback.id)
        self.assertTrue(updated_feedback.viewed_by_doctor)
