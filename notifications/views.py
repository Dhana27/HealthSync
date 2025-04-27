from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
from django.urls import reverse
from .models import (
    MedicationSchedule, Appointment, Patient, Doctor, ConsultRequest, 
    Prescription, Medication, MedicalHistory, MedicalHistoryMedication,
    PatientFeedback
)
from recovery.models import RecoveryTip
from .forms import MedicationReminderForm, AppointmentReminderForm, DietTipForm, MedicalHistoryForm, MedicalHistoryMedicationForm
from core.models import Message  # Import Message model from core app
from django.contrib.auth.models import Group, User
from notifications.tasks import send_appointment_reminders
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.conf import settings
from django.template.loader import render_to_string, get_template
from xhtml2pdf import pisa
from .create_room import create_room
from notifications.token_utils import generate_token_for_user
import jwt
from django.utils.timezone import now, make_aware
from datetime import timedelta
import openai
import json
from django.utils import timezone
from django.utils.dateparse import parse_datetime

import logging, io, time
import random, string


logger = logging.getLogger(__name__)


# ✅ Universal Function: Determine User Role
def get_user_role(user):
    """Returns 'doctor', 'patient', or 'admin' based on user's group."""
    if user.groups.filter(name="Doctor").exists():
        return "doctor"
    elif user.groups.filter(name="Patient").exists():
        return "patient"
    elif user.is_superuser:
        return "admin"
    return "unknown"


# Doctors Only - Manage Patient Health
@login_required
def manage_patient_health(request, patient_id):
    """Doctors and admins can view and manage patient health records"""
    role = get_user_role(request.user)
    if role not in ["doctor", "admin"] and not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    patient = get_object_or_404(Patient, id=patient_id)
    
    # Fetch medical history and medication schedules
    medical_history = MedicalHistory.objects.filter(patient=patient).order_by("-date", "-time")
    medication_schedules = MedicationSchedule.objects.filter(patient=patient).order_by("-date", "-time")

    # Initialize forms - only for doctors
    app_form = None
    diet_form = None
    if role == "doctor":
        app_form = AppointmentReminderForm()
        diet_form = DietTipForm()

    if request.method == "POST" and role == "doctor":
        form_type = request.POST.get("form_type")

        if form_type == "consultation":
            try:
                # Create medical history entry
                history = MedicalHistory.objects.create(
                    patient=patient,
                    doctor=request.user.doctor,
                    date=now().date(),
                    time=now().time(),
                    diagnosis=request.POST.get("diagnosis"),
                    symptoms=request.POST.get("symptoms")
                )

                # Handle multiple medications
                medication_names = request.POST.getlist("medication_name[]")
                dosages = request.POST.getlist("dosage[]")
                times = request.POST.getlist("time[]")
                duration_days_list = request.POST.getlist("duration_days[]")
                food_timings = request.POST.getlist("food_timing[]")

                for i in range(len(medication_names)):
                    if medication_names[i]:  # Only create if medication name is provided
                        # Convert time string to time object
                        try:
                            time_obj = datetime.strptime(times[i], '%H:%M').time()
                        except ValueError:
                            messages.error(request, f"Invalid time format for medication {medication_names[i]}")
                            continue

                        # Create medical history medication
                        MedicalHistoryMedication.objects.create(
                            medical_history=history,
                            medication_name=medication_names[i],
                            dosage=dosages[i],
                            duration_days=int(duration_days_list[i]),
                            food_timing=food_timings[i]
                        )
                        
                        # Create medication schedule for reminders
                        medication = MedicationSchedule(
                            patient=patient,
                            medication_name=medication_names[i],
                            dosage=dosages[i],
                            date=now().date(),
                            time=time_obj,  # Use the converted time object
                            duration_days=int(duration_days_list[i]),
                            food_timing=food_timings[i]
                        )
                        medication.save()
                        medication.schedule_sms_reminder()
                
                messages.success(request, "✅ Consultation has been recorded and medication reminders have been set!")
                return redirect("manage_patient_health", patient_id=patient.id)
            
            except Exception as e:
                messages.error(request, f"Error saving consultation: {str(e)}")
                return redirect("manage_patient_health", patient_id=patient.id)

        elif form_type == "appointment":
            app_form = AppointmentReminderForm(request.POST)
            if app_form.is_valid():
                appointment = app_form.save(commit=False)
                appointment.patient = patient
                appointment.save()
                messages.success(request, "✅ Appointment has been set.")
                return redirect("manage_patient_health", patient_id=patient.id)

        elif form_type == "diet_tip":
            diet_form = DietTipForm(request.POST)
            if diet_form.is_valid():
                tip = diet_form.save(commit=False)
                tip.doctor = request.user.doctor
                tip.patient = patient  # Add this line to fix the NOT NULL constraint error
                tip.save()
                messages.success(request, "✅ Diet tip has been added.")
                return redirect("manage_patient_health", patient_id=patient.id)

    context = {
        "medication_schedules": medication_schedules,
        "medical_history": medical_history,
        "patient": patient,
        "role": role
    }
    
    # Only add forms to context if user is a doctor
    if role == "doctor":
        context.update({
            "app_form": app_form,
            "diet_form": diet_form
        })

    return render(request, "manage_patient_health.html", context)

# Patients Only - View Their Health Updates
@login_required
def view_reminders(request):
    """Patients can see their upcoming medications, appointments, and recovery tips."""
    role = get_user_role(request.user)
    if role != "patient":
        messages.error(request, "Access denied.")
        return redirect("home")

    patient = getattr(request.user, "patient", None)
    if not patient:
        messages.error(request, "No patient profile found.")
        return redirect("home")

    current_datetime = now()
    
    # Get active medications (not older than end date)
    medication_reminders = MedicationSchedule.objects.filter(
        patient=patient,
        end_date__gte=current_datetime.date()
    ).order_by("date", "time")

    # Update status for medications that have ended
    MedicationSchedule.objects.filter(
        patient=patient,
        end_date__lt=current_datetime.date(),
        reminder_status__in=['pending', 'sent', 'overdue', 'missed']
    ).update(reminder_status='ended')
    
    appointments = Appointment.objects.filter(
        patient=patient,
        appointment_date__gte=current_datetime.date()
    ).order_by("appointment_date", "appointment_time").exclude(
        appointment_date=current_datetime.date(),
        appointment_time__lt=current_datetime.time()
    )
    
    medical_history = MedicalHistory.objects.filter(
        patient=patient
    ).prefetch_related(
        'medications'
    ).order_by("-date", "-time")

    # Get recovery tips for each medical history entry
    recovery_tips = RecoveryTip.objects.filter(
        patient=patient
    ).order_by('-created_at')

    return render(request, "view_reminders.html", {
        "medication_reminders": medication_reminders,
        "appointments": appointments,
        "medical_history": medical_history,
        "recovery_tips": recovery_tips,
        "role": "patient"
    })

@login_required
def request_consultation(request, doctor_id):
    doctor_obj = get_object_or_404(Doctor, id=doctor_id)
    user = doctor_obj.user  # get linked user
    if request.method == 'POST':
        consult = ConsultRequest.objects.create(patient=request.user, doctor=user)
        
        # If this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'redirect_url': reverse('my_consult_status', args=[consult.id])
            })
            
        # For non-AJAX requests
        messages.success(request, f"You've been added to the queue for {doctor_obj}.")
        return redirect('my_consult_status', consult_id=consult.id)
    
    # Handle GET requests
    return redirect('available_doctors')

@login_required
def check_consult_status(request):
    print(f"[CHECK STATUS] Request by: {request.user}")
    consult = ConsultRequest.objects.filter(
        patient=request.user,
        status__in=["pending", "accepted"]
    ).order_by('-created_at').first()

    print(f"[CHECK STATUS] Patient: {request.user}, Consult ID: {consult.id if consult else None}, Status: {consult.status if consult else None}, Room: {consult.room_url if consult else None}")

    if consult:
        print(f"[CONSULT FOUND] Status: {consult.status}, Room URL: {consult.room_url}")
        return JsonResponse({
            "status": consult.status,
            "consult_id": consult.id if consult.status == "accepted" else None,
            "room_url": consult.room_url
        })
    return JsonResponse({"status": "waiting"})

@login_required
def cancel_consultation(request, consult_id):
    consult = get_object_or_404(ConsultRequest, id=consult_id, patient=request.user)

    if request.method == "POST" and consult.status in ["pending", "accepted"]:
        consult.status = "cancelled"
        consult.save()
        messages.success(request, "Your consultation request has been cancelled.")
    
    return redirect('available_doctors')

@login_required
def doctor_consultation_room(request):
    if get_user_role(request.user) != "doctor":
        return redirect('home')

    waiting_patients = ConsultRequest.objects.filter(doctor=request.user, status='pending').order_by('created_at')
    return render(request, 'doctor_consult_room.html', {"patients": waiting_patients})

@login_required
def accept_consultation(request, consult_id):
    consult = get_object_or_404(ConsultRequest, id=consult_id, doctor=request.user)

    if consult.status != "pending":
        return redirect('doctor_consultation_room')

    consult.status = "accepted"
    consult.save()

    return redirect('start_call', consult_id=consult.id)


@login_required
def create_prescription(request, consult_id):
    consult = get_object_or_404(ConsultRequest, id=consult_id, doctor=request.user)

    if request.method == "POST":
        diagnosis = request.POST["diagnosis"]
        advice = request.POST["advice"]
        med_names = request.POST.getlist("med_name[]")
        food_timings = request.POST.getlist("food_timing[]")
        times_per_day = request.POST.getlist("times_per_day[]")

        prescription = Prescription.objects.create(
            doctor=request.user,
            patient=consult.patient,
            diagnosis=diagnosis,
            advice=advice,
        )

        for name, food, times in zip(med_names, food_timings, times_per_day):
            Medication.objects.create(
                prescription=prescription,
                name=name,
                food_timing=food,
                times_per_day=int(times)
            )

        messages.success(request, "Prescription created successfully.")
        consult.prescription = prescription
        consult.save()
        return redirect("doctor_consultation_room")

    return render(request, "prescription_form.html", {"consult": consult})


def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    return result.getvalue() if not pdf.err else None

@login_required
def view_prescription_pdf(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id)
    if request.user not in [prescription.patient, prescription.doctor]:
        return HttpResponseForbidden()

    pdf = render_to_pdf("prescription_pdf.html", {"prescription": prescription})
    return HttpResponse(pdf, content_type='application/pdf')


@login_required
def my_consult_status(request, consult_id):
    consult = get_object_or_404(ConsultRequest, id=consult_id, patient=request.user)

    queue = ConsultRequest.objects.filter(
        doctor=consult.doctor,
        status='pending',
        created_at__lt=consult.created_at
    ).count()

    return render(request, 'my_consult_status.html', {
        'consult': consult,
        'queue_position': queue
    })

"""@login_required
def start_call(request, consult_id):
    consult = get_object_or_404(ConsultRequest, id=consult_id)

    # Create room ONLY if doctor and room doesn't already exist
    if not consult.room_url or not consult.room_id:
        response = create_room()
        consult.room_url = response["room_code"]
        consult.room_id = response["room_id"]       # For token generation
        consult.save()

    # Determine role
    role = "doctor" if request.user == consult.doctor else "patient"

    # Make sure consult.room_id exists
    token = generate_token_for_user(request.user, role, consult.room_id)

    return render(request, "call_room.html", {
        "room_code": consult.room_url,   # used in iframe
        "hms_token": token,
        "consult_id": consult.id,
        "role": role,
    })"""

@login_required
def start_call(request, consult_id):
    consult = get_object_or_404(ConsultRequest, id=consult_id)

    # Hardcoded static room codes
    if request.user == consult.doctor:
        join_url = "https://healthsync-videoconf-1025.app.100ms.live/meeting/mfm-merv-nny"
    else:
        join_url = "https://healthsync-videoconf-1025.app.100ms.live/meeting/ywp-bmrv-jlw"

    return render(request, "call_room.html", {
        "join_url": join_url,
        "role": "doctor" if request.user == consult.doctor else "patient",
        "consult_id": consult.id,
    })


@login_required
def complete_consult(request, consult_id):
    if request.method == "POST":
        consult = get_object_or_404(ConsultRequest, id=consult_id, doctor=request.user)
        consult.status = "completed"
        consult.save()
        return JsonResponse({"success": True})
    
    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

@login_required
def toggle_availability(request):
    if get_user_role(request.user) != "doctor":
        return redirect('home')

    doctor = Doctor.objects.get(user=request.user)
    doctor.is_available_for_call = not doctor.is_available_for_call
    doctor.save()
    return redirect('doctor_consultation_room')

@login_required
def available_doctors(request):
    doctors = Doctor.objects.filter(is_available_for_call=True)

    # 🔁 ALL consults by this patient (not just current)
    consults = ConsultRequest.objects.filter(
        patient=request.user
    ).select_related('doctor', 'prescription').order_by('-created_at')

    context = {
        "doctors": doctors,
        "consults": consults,  # for history
    }

    return render(request, "available_doctors.html", context)

"""def generate_100ms_token(request):
    role = request.GET.get('role', 'guest')  # 'doctor' or 'patient'
    room_id = settings.HMS_ROOM_ID  # If you want static room
    user_id = str(request.user.id)

    payload = {
        "access_key": settings.HMS_ACCESS_KEY,
        "type": "app",
        "version": 2,
        "room_id": room_id,
        "user_id": user_id,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
      }

    token = jwt.encode(payload, settings.HMS_SECRET, algorithm="HS256")
    return JsonResponse({"token": token})

@login_required
def join_call(request, doctor_id):
    room_url = create_daily_room()
    return render(request, "call_room.html", {"room_url": room_url})"""

"""#  Doctors Only - View Messages from Patients
@login_required
def doctor_messages(request):
    # Doctors can see a list of all their patients' messages.
    role = get_user_role(request.user)
    if role != "doctor":
        messages.error(request, "Access denied.")
        return redirect("home")

    conversations = Message.objects.filter(recipient=request.user).values("sender").distinct()

    return render(request, "doctor_messages.html", {
        "conversations": conversations,
        "role": "doctor"
    })


# Doctor-Patient Chat View
@login_required
def chat_detail(request, patient_id):
    # Displays chat between doctor and specific patient.
    role = get_user_role(request.user)
    if role != "doctor":
        messages.error(request, "Access denied.")
        return redirect("home")

    patient = get_object_or_404(User, id=patient_id)
    messages_list = Message.objects.filter(
        Q(sender=patient, recipient=request.user) | Q(sender=request.user, recipient=patient)
    ).order_by("timestamp")

    return render(request, "chat_detail.html", {
        "patient": patient,
        "messages": messages_list,
        "role": "doctor"
    })
"""

@login_required
def fitbit_logout(request):
    """Disconnect Fitbit from the user's account."""
    if request.method == "POST":
        patient = request.user.patient
        patient.fitbit_access_token = None
        patient.fitbit_refresh_token = None
        patient.fitbit_connected = False
        patient.save()
        messages.success(request, "Successfully disconnected from Fitbit.")
    return redirect('patient_dashboard')

@login_required
def mark_medication_taken(request, medication_id):
    """Mark a medication as taken"""
    medication = get_object_or_404(MedicationSchedule, id=medication_id)
    
    # Security check - only the patient can mark their own medications
    if medication.patient.user != request.user:
        return HttpResponseForbidden("You can only mark your own medications as taken")
    
    if request.method == 'POST':
        medication.mark_as_taken()
        messages.success(request, f"✅ {medication.medication_name} marked as taken!")
        
        # If this was called via AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
            
        return redirect('view_reminders')
    else:
        # For GET requests, redirect to the reminders view
        return redirect('view_reminders')

@login_required
def submit_feedback(request):
    if get_user_role(request.user) != "patient":
        return redirect('home')
        
    if request.method == 'POST':
        try:
            feedback_text = request.POST.get('feedback')
            pain_level = int(request.POST.get('pain_level'))
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Enhanced prompt for health analysis
            system_prompt = """You are a healthcare assistant specialized in patient follow-up analysis. 
            Given patient feedback and pain level, analyze the severity and urgency of their condition.
            Consider the following in your analysis:
            - Pain level (0-10 scale)
            - Symptoms described
            - Any concerning patterns or red flags
            - Potential underlying conditions
            - Required follow-up actions
            
            Return a JSON response with the following structure:
            {
                "sentiment_label": "positive" | "neutral" | "negative",
                "severity_level": "mild" | "moderate" | "severe",
                "urgency": "low" | "medium" | "high",
                "follow_up_needed": true | false,
                "reasoning": "<detailed explanation of your analysis>",
                "recommended_actions": ["action1", "action2", ...]
            }"""
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Pain Level: {pain_level}/10\nFeedback: {feedback_text}"}
                ],
                response_format={ "type": "json_object" }
            )
            
            analysis_data = json.loads(response.choices[0].message.content)
            
            # Save feedback with analysis
            feedback = PatientFeedback.objects.create(
                patient=request.user,
                feedback_text=feedback_text,
                pain_level=pain_level,
                sentiment_label=analysis_data['sentiment_label'],
                severity_level=analysis_data['severity_level'],
                urgency=analysis_data['urgency'],
                follow_up_needed=analysis_data['follow_up_needed'],
                reasoning=analysis_data['reasoning'],
                consultation_recommended=analysis_data['follow_up_needed']
            )
            
            # If it's an AJAX request, return the analysis data
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Clean up the reasoning text
                reasoning = analysis_data['reasoning']
                reasoning = reasoning.replace('The patient', 'You').replace('the patient', 'you')
                reasoning = reasoning.replace('You is', 'You are').replace('you is', 'you are')
                reasoning = reasoning.replace("You's", "Your").replace("you's", "your")
                reasoning = reasoning.replace("You reports", "You reported").replace("you reports", "you reported")
                # Remove duplicate pain level information
                reasoning = reasoning.replace(f'with a pain level of {pain_level}/10', '').replace(f'at a level of {pain_level}/10', '')
                reasoning = reasoning.replace(f'The pain level of {pain_level}/10', '')
                reasoning = reasoning.replace(f'pain level of {pain_level}/10', '')
                reasoning = reasoning.replace(f'A also suggests', 'This also suggests')
                
                return JsonResponse({
                    'status': 'success',
                    'severity_level': analysis_data['severity_level'],
                    'urgency': analysis_data['urgency'],
                    'reasoning': reasoning,
                    'recommended_actions': analysis_data['recommended_actions'],
                    'message': f"Based on your symptoms and pain level ({pain_level}/10), {reasoning}"
                })
            
            # For non-AJAX requests, handle as before
            if analysis_data['severity_level'] in ['severe', 'moderate'] or analysis_data['urgency'] in ['high', 'medium']:
                messages.warning(request, f"Based on your symptoms, we recommend immediate consultation with a doctor. {analysis_data['reasoning'].replace('The patient', 'You').replace('the patient', 'you')}")
                return redirect('available_doctors')
            else:
                self_care_message = f"Thank you for your health update. {analysis_data['reasoning'].replace('The patient', 'You').replace('the patient', 'you')}\n\nRecommended actions:\n" + "\n".join(f"- {action}" for action in analysis_data['recommended_actions'])
                messages.success(request, self_care_message)
                return redirect('patient_dashboard')
                
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Error in health analysis: {str(e)}\n{error_traceback}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Sorry, there was an error processing your health update. Please try again later.',
                    'error_details': str(e),
                    'error_type': type(e).__name__,
                    'traceback': error_traceback
                }, status=500)
            messages.error(request, "Sorry, there was an error processing your health update. Please try again later.")
            return redirect('patient_dashboard')
            
    return render(request, 'patient_feedback.html')

@login_required
def admin_medical_history(request, patient_id):
    """Admin view for patient medical history"""
    if not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        patient = get_object_or_404(Patient, id=patient_id)
    except:
        messages.error(request, f"Patient with ID {patient_id} does not exist.")
        return redirect("admin:index")  # Redirect back to admin dashboard
    
    # Fetch medical history and medication schedules
    medical_history = MedicalHistory.objects.filter(patient=patient).order_by("-date", "-time")
    medication_schedules = MedicationSchedule.objects.filter(patient=patient).order_by("-date", "-time")

    context = {
        "medication_schedules": medication_schedules,
        "medical_history": medical_history,
        "patient": patient,
        "role": "admin"
    }

    return render(request, "admin_medical_history.html", context)

@login_required
def admin_patient_list(request):
    """Admin view to list all patients and their records"""
    if not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    # Get all patients with their latest appointment
    patients = Patient.objects.all().select_related('user').prefetch_related(
        'appointment_set'  # For getting appointments
    )

    patient_data = []
    for patient in patients:
        latest_appointment = patient.appointment_set.order_by('-appointment_date', '-appointment_time').first()
        patient_data.append({
            'patient': patient,
            'created_at': patient.user.date_joined,  # Use user's date_joined instead
            'last_appointment_date': latest_appointment.appointment_date if latest_appointment else None,
            'last_appointment_time': latest_appointment.appointment_time if latest_appointment else None
        })

    return render(request, "admin_patient_list.html", {
        "patient_data": patient_data,
        "role": "admin"
    })

@login_required
def admin_appointments(request):
    """Admin view to list all appointments"""
    if not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    appointments = Appointment.objects.all().select_related(
        'doctor__user',  # For doctor's name
        'patient'        # For patient's name
    ).order_by('-appointment_date', '-appointment_time')

    return render(request, "admin_appointments.html", {
        "appointments": appointments,
        "role": "admin"
    })

def debug_appointments(request):
    """Debug view to display appointments directly"""
    from .models import Appointment
    appointments = Appointment.objects.all()
    return render(request, 'notifications/debug_appointments.html', {
        'appointments': appointments
    })

def check_medication_status(request, medication_id):
    """
    Check and return the current status of a medication reminder.
    Updates status based on current time and date.
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        medication = MedicationSchedule.objects.get(id=medication_id)
        
        # Check if user owns this medication
        if medication.patient.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        now = timezone.now()
        
        # Check if medication has ended
        if now.date() > medication.end_date:
            if medication.reminder_status != 'ended':
                medication.reminder_status = 'ended'
                medication.last_status_date = now.date()
                medication.save()
            return JsonResponse({
                'status': 'ended',
                'last_updated': medication.last_status_date.isoformat()
            })
        
        # If medication is already taken, don't change the status
        if medication.reminder_status == 'taken':
            return JsonResponse({
                'status': medication.reminder_status,
                'last_updated': medication.last_status_date.isoformat()
            })
            
        medication_time = timezone.make_aware(
            timezone.datetime.combine(medication.date, medication.time)
        )
        
        # Reset status at midnight if not taken
        if now.date() > medication.last_status_date:
            medication.reminder_status = 'pending'
            medication.last_status_date = now.date()
            medication.save()
        
        # Update status based on current time
        if medication.reminder_status == 'pending':
            if now >= medication_time:
                medication.reminder_status = 'sent'
                medication.save()
            
            if now > medication_time + timezone.timedelta(hours=1):
                medication.reminder_status = 'overdue'
                medication.save()
            
            if now.date() > medication_time.date():
                medication.reminder_status = 'missed'
                medication.save()
        
        return JsonResponse({
            'status': medication.reminder_status,
            'last_updated': medication.last_status_date.isoformat()
        })
        
    except MedicationSchedule.DoesNotExist:
        return JsonResponse({'error': 'Medication not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def messages_view(request):
    """Doctor sees patient list & full conversation with selected patient."""
    if get_user_role(request.user) != "doctor":
        return redirect('patients_list')

    patients = Patient.objects.all()
    messages_overview = {}

    for patient in patients:
        # Get latest message with timestamp for sorting
        latest_message = Message.objects.filter(
            Q(sender=patient.user, recipient=request.user) |
            Q(sender=request.user, recipient=patient.user)
        ).order_by('-timestamp').first()

        # Get unread message count
        unread_count = Message.objects.filter(
            sender=patient.user,
            recipient=request.user,
            is_read=False
        ).count()

        # Get next appointment
        next_appointment = Appointment.objects.filter(
            patient=patient,
            appointment_date__gte=timezone.now().date()
        ).order_by('appointment_date', 'appointment_time').first()

        messages_overview[patient] = {
            'latest_message': latest_message,
            'next_appointment': next_appointment,
            'message_time': latest_message.timestamp if latest_message else None,
            'unread_count': unread_count
        }

    # Sort patients by latest message time
    min_datetime = timezone.make_aware(datetime.min)
    sorted_patients = sorted(
        patients,
        key=lambda p: messages_overview[p]['message_time'] if messages_overview[p]['message_time'] else min_datetime,
        reverse=True
    )

    selected_patient_username = request.GET.get("selected_patient")
    selected_patient = None
    messages_list = None

    if selected_patient_username:
        selected_patient = get_object_or_404(User, username=selected_patient_username)
        
        # Handle AJAX request for new messages
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            after_timestamp = request.GET.get('after_timestamp')
            if after_timestamp:
                try:
                    after_timestamp = parse_datetime(after_timestamp)
                    if timezone.is_naive(after_timestamp):
                        after_timestamp = timezone.make_aware(after_timestamp)
                    
                    new_messages = Message.objects.filter(
                        Q(sender=request.user, recipient=selected_patient) | 
                        Q(sender=selected_patient, recipient=request.user),
                        timestamp__gt=after_timestamp
                    ).order_by('timestamp')
                    
                    messages_data = [{
                        'id': str(message.id),
                        'content': message.content.replace('PATIENT: ', '').replace('URGENT: ', '').replace('ESCALATION: ', ''),
                        'is_sent': message.sender == request.user,
                        'sender_name': message.sender.username,
                        'timestamp': message.timestamp.strftime('%b %d, %Y %H:%M')
                    } for message in new_messages]
                    
                    return JsonResponse({'messages': messages_data})
                except (ValueError, TypeError):
                    return JsonResponse({'messages': []})
        
        # Get messages in chronological order (oldest first)
        messages_list = Message.objects.filter(
            Q(sender=request.user, recipient=selected_patient) | 
            Q(sender=selected_patient, recipient=request.user)
        ).order_by('timestamp')
        
        # Mark messages as read when doctor views them
        messages_list.filter(recipient=request.user).update(is_read=True)
    
        if request.method == "POST":
            message_content = request.POST.get("message")
            if message_content:
                new_message = Message.objects.create(
                    sender=request.user,
                    recipient=selected_patient,
                    content=message_content,
                    is_read=False
                )
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': {
                            'id': str(new_message.id),
                            'content': new_message.content,
                            'is_sent': True,
                            'sender_name': request.user.username,
                            'timestamp': new_message.timestamp.strftime('%b %d, %Y %H:%M')
                        }
                    })
                return redirect(reverse("messages") + f"?selected_patient={selected_patient_username}")

    return render(request, 'messages.html', {
        "patients": sorted_patients,
        "messages_overview": messages_overview,
        "selected_patient": selected_patient,
        "messages_list": messages_list,
        "role": "doctor"
    })

@login_required
def check_new_messages(request):
    """
    Check for new messages since the last check time.
    Also returns unread counts per patient if requested.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        # Get the last check time from the request
        last_check_time = request.GET.get('last_check_time')
        if last_check_time:
            try:
                last_check_time = parse_datetime(last_check_time)
                if timezone.is_naive(last_check_time):
                    last_check_time = timezone.make_aware(last_check_time)
            except (ValueError, TypeError):
                last_check_time = None

        # If requesting unread counts
        if request.GET.get('get_unread_counts'):
            unread_counts = {}
            patients = Patient.objects.all()
            for patient in patients:
                count = Message.objects.filter(
                    sender=patient.user,
                    recipient=request.user,
                    is_read=False
                ).count()
                if count > 0:
                    unread_counts[patient.user.username] = count
            
            return JsonResponse({
                'unread_counts': unread_counts,
                'current_time': timezone.now().isoformat()
            })
        
        # Regular new message check - check for ANY unread messages
        has_new_messages = Message.objects.filter(
            recipient=request.user,
            is_read=False
        ).exists()
        
        return JsonResponse({
            'has_new_messages': has_new_messages,
            'current_time': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in check_new_messages: {str(e)}")
        return JsonResponse({
            'error': 'Server error',
            'details': str(e)
        }, status=500)