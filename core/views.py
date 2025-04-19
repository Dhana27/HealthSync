from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db.models import Q
from notifications.models import Doctor, Patient
from .models import Message, FitbitVitals
from .forms import ChatForm, PatientRegisterForm, PatientProfileForm, UserProfileForm, DoctorProfileForm
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from .chatbot import ai_chatbot_response
from django.urls import reverse
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
import json
import requests
import random


# Fitbit OAuth endpoints
AUTH_URL = 'https://www.fitbit.com/oauth2/authorize'
TOKEN_URL = 'https://api.fitbit.com/oauth2/token'
API_URL = 'https://api.fitbit.com/1/user/-/activities/heart/date/today/1d.json'

def global_data(request):
    return {"site_name": "Patient Follow-up System"}


### AUTHENTICATION ###
def home_view(request):
    """Render homepage with only HealthSync title & login button."""
    return render(request, 'home.html')

def login_view(request):
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            role = get_user_role(user)
            if role == 'patient':
                return redirect('view_reminders')
            elif role == 'doctor':
                return redirect('patients_list')
            elif role == 'admin':
                return redirect('/admin/')
            messages.error(request, 'User role not recognized.')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html', {'form': form})

def register_patient(request):
    if request.method == "POST":
        form = PatientRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            Patient.objects.create(
                user=user,
                email=form.cleaned_data['email'],
                phone_number=form.cleaned_data.get('phone_number'),
                role='patient'
            )
            group = Group.objects.get_or_create(name='Patient')[0]
            user.groups.add(group)
            login(request, user)
            return redirect('patient_dashboard')
    else:
        form = PatientRegisterForm()
    return render(request, 'register.html', {'form': form})


def logout_view(request):
    """Logout user and redirect to home."""
    logout(request)
    return redirect('home')

### ROLE-BASED UTILITY FUNCTION ###
def get_user_role(user):
    """Returns the role of the logged-in user."""
    if user.is_authenticated:
        if user.groups.filter(name="Doctor").exists():
            return "doctor"
        elif user.groups.filter(name="Patient").exists():
            return "patient"
        elif user.is_superuser:
            return "admin"
    return None

def base_context_processor(request):
    """Ensure role is available globally in templates."""
    context = {"role": None}  # Default context

    if not request.user.is_authenticated:
        return context

    if request.user.groups.filter(name="Doctor").exists():
        context["role"] = "doctor"
        # Add chat messages and form for the chat widget
        raw_messages = Message.objects.filter(
            Q(sender=request.user) | Q(recipient=request.user)
        ).order_by("timestamp")

        messages_list = []
        for msg in raw_messages:
            sender_label = msg.sender.username
            role_label = "patient"  # Default role
            display_content = msg.content

            # Determine role and sender based on message content and sender/recipient
            if msg.content.startswith("BOT:"):
                sender_label = "Healthsync Virtual Assistant"
                role_label = "bot"
                display_content = msg.content.replace("BOT: ", "")
            elif msg.content.startswith("PATIENT:"):
                if msg.sender == request.user:
                    sender_label = "You"
                    role_label = "patient"
                else:
                    sender_label = msg.sender.username
                    role_label = "patient"
                display_content = msg.content.replace("PATIENT: ", "")
            elif msg.sender.groups.filter(name="Doctor").exists():
                sender_label = f"Dr. {msg.sender.username}"
                role_label = "doctor"

            messages_list.append({
                "sender": sender_label,
                "role": role_label,
                "content": display_content,
                "timestamp": msg.timestamp
            })

        context["chat_messages"] = messages_list
        context["chat_form"] = ChatForm()
    elif request.user.groups.filter(name="Patient").exists():
        context["role"] = "patient"
    elif request.user.is_superuser:
        context["role"] = "admin"
    
    return context

@login_required
def edit_patient_profile(request):
    patient = request.user.patient

    if request.method == "POST":
        form = PatientProfileForm(request.POST, instance=patient)
        user_form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid() and user_form.is_valid():
            form.save()
            user_form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("edit_patient_profile")
    else:
        form = PatientProfileForm(instance=patient)
        user_form = UserProfileForm(instance=request.user)

    return render(request, "edit_patient_profile.html", {
        "form": form,
        "user_form": user_form
    })

@login_required
def edit_doctor_profile(request):
    if not hasattr(request.user, 'doctor'):
        messages.error(request, "You are not authorized to edit a doctor profile.")
        return redirect("home")

    doctor = request.user.doctor

    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=request.user)
        doctor_form = DoctorProfileForm(request.POST, instance=doctor)
        if user_form.is_valid() and doctor_form.is_valid():
            user_form.save()
            doctor_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('edit_doctor_profile')
    else:
        user_form = UserProfileForm(instance=request.user)
        doctor_form = DoctorProfileForm(instance=doctor)

    return render(request, 'edit_doctor_profile.html', {
        'user_form': user_form,
        'doctor_form': doctor_form
    })

@login_required
def fitbit_login(request):
    fitbit = OAuth2Session(
        client_id=settings.FITBIT_CLIENT_ID,
        redirect_uri=settings.FITBIT_REDIRECT_URI,
        scope=settings.FITBIT_SCOPE
    )
    auth_url, _ = fitbit.authorization_url(AUTH_URL)
    return redirect(auth_url)

@login_required
def fitbit_callback(request):
    code = request.GET.get('code')
    if not code:
        return HttpResponse("Access was denied or failed. Please try again.")
    oauth = OAuth2Session(settings.FITBIT_CLIENT_ID, redirect_uri=settings.FITBIT_REDIRECT_URI)

    token = oauth.fetch_token(
        TOKEN_URL,
        code=code,
        auth=HTTPBasicAuth(settings.FITBIT_CLIENT_ID, settings.FITBIT_CLIENT_SECRET)
    )

    access_token = token.get('access_token')
    headers = {'Authorization': f'Bearer {access_token}'}

    response = requests.get(API_URL, headers=headers)
    hr_data = response.json()

    patient = request.user.patient  # assuming this relation exists
    patient.fitbit_access_token = token['access_token']
    patient.fitbit_refresh_token = token['refresh_token']
    patient.fitbit_connected = True
    patient.save()

    # Extract resting heart rate (adjust path as needed)
    try:
        rhr = hr_data['activities-heart'][0]['value']['restingHeartRate']
    except:
        rhr = None

    # Just for testing, assign to the first user in your DB
    user = request.user  # Replace with actual user later

    # Store in DB
    vitals = FitbitVitals.objects.create(
        user=user,
        date=timezone.now().date(),
        resting_heart_rate=rhr,
        alert_triggered=False  # We'll update this if alert triggered
    )

    # Step 4: Trigger alert if needed
    if rhr and rhr > 130:
        vitals.alert_triggered = True
        vitals.save()
        print("🚨 ALERT: High resting heart rate detected!")

    return render(request, 'fitbit_callback_success.html')


@login_required
def patient_dashboard_view(request):
    user = request.user
    #role = get_user_role(request.user)
    if get_user_role(user) == "doctor" and request.GET.get("patient_id"):
        patient = get_object_or_404(Patient, id=request.GET["patient_id"])
        user = patient.user

    # Pull last 7 days of vitals
    vitals = FitbitVitals.objects.filter(user=user).order_by('-date', '-id')[:7][::-1]

    hr_data = [v.resting_heart_rate for v in vitals if v.resting_heart_rate is not None]
    spo2_data = [v.spo2 for v in vitals if v.spo2 is not None]
    sleep_data = [v.sleep_minutes for v in vitals if v.sleep_minutes is not None]
    temp_data = [v.body_temp for v in vitals if v.body_temp is not None]
    labels = [v.date.strftime('%b %d') for v in vitals]

    context = {
        "hr_data": json.dumps(hr_data or [0], cls=DjangoJSONEncoder),
        "spo2_data": json.dumps(spo2_data or [0], cls=DjangoJSONEncoder),
        "sleep_data": json.dumps(sleep_data or [0], cls=DjangoJSONEncoder),
        "temp_data": json.dumps(temp_data or [0], cls=DjangoJSONEncoder),
        "labels": json.dumps(labels or ["No Data"], cls=DjangoJSONEncoder),
    }
    recent_vitals = FitbitVitals.objects.filter(user=user).order_by('-id')[:5]  # Last 5 vitals
    context["recent_vitals"] = recent_vitals

    return render(request, "patient_dashboard.html", context)

### PATIENT VIEWS ###
@login_required
def patient_chat_view(request):
    """Patient interacts with chatbot or escalates issue to doctor."""
    chatbot_response = None
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == "POST":
        form = ChatForm(request.POST)
        if form.is_valid():
            user_message = form.cleaned_data["message"]
            try:
                patient = request.user.patient
                assigned_doctor = patient.assigned_doctor
            except Patient.DoesNotExist:
                assigned_doctor = None

            # Check if this is an escalation to doctor
            is_escalation = request.POST.get('escalate') == '1'
            
            if is_escalation:
                if assigned_doctor:
                    # Create patient's message
                    Message.objects.create(
                        sender=request.user,
                        recipient=assigned_doctor.user,
                        content=f"PATIENT: {user_message}"
                    )
                    if is_ajax:
                        return JsonResponse({
                            "status": "success",
                            "is_escalated": True,
                            "message": "Message sent to doctor successfully."
                        })
                    return redirect("patient_chat")
                else:
                    if is_ajax:
                        return JsonResponse({"error": "No doctor assigned to you. Please contact support."}, status=400)
                    messages.error(request, "No doctor assigned to you. Please contact support.")
            else:
                # This is a message for the bot
                chatbot_response = ai_chatbot_response(user_message)
                Message.objects.create(
                    sender=request.user,
                    recipient=request.user,
                    content=f"PATIENT: {user_message}"
                )
                Message.objects.create(
                    sender=request.user,
                    recipient=request.user,
                    content=f"BOT: {chatbot_response}"
                )
                
                if is_ajax:
                    return JsonResponse({
                        "status": "success",
                        "is_escalated": False,
                        "bot_response": chatbot_response
                    })
            return redirect("patient_chat")
    else:
        form = ChatForm()

    raw_messages = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).order_by("timestamp")

    # Preprocess for display
    messages_list = []
    for msg in raw_messages:
        sender_label = msg.sender.username
        role_label = "patient"  # Default role
        display_content = msg.content

        # Determine role and sender based on message content and sender/recipient
        if msg.content.startswith("BOT:"):
            sender_label = "Healthsync Virtual Assistant"
            role_label = "bot"
            display_content = msg.content.replace("BOT: ", "")
        elif msg.content.startswith("PATIENT:"):
            if msg.sender == request.user:
                sender_label = "You"
                role_label = "patient"
            else:
                sender_label = msg.sender.username
                role_label = "patient"
            display_content = msg.content.replace("PATIENT: ", "")
        elif msg.sender.groups.filter(name="Doctor").exists():
            sender_label = f"Dr. {msg.sender.username}"
            role_label = "doctor"

        messages_list.append({
            "sender": sender_label,
            "role": role_label,
            "content": display_content,
            "timestamp": msg.timestamp.strftime("%b %d, %Y %H:%M")
        })

    context = {
        "form": form,
        "chatbot_response": chatbot_response,
        "messages_list": messages_list
    }

    if is_ajax:
        chat_html = """
        <div class="chat-content">
            <div class="chat-messages" id="conversationList">
                {% for msg in messages_list %}
                    <div class="message {% if msg.role == 'doctor' %}doctor-message{% elif msg.role == 'bot' %}bot-message{% else %}patient-message{% endif %}">
                        <div class="message-sender">{{ msg.sender }}</div>
                        <div class="message-content">{{ msg.content }}</div>
                        <div class="message-time">{{ msg.timestamp }}</div>
                    </div>
                {% empty %}
                    <div class="no-messages">No messages yet. Start a conversation!</div>
                {% endfor %}
            </div>
            <div class="chat-input">
                <form method="POST" id="chatForm">
                    {% csrf_token %}
                    <div class="input-group">
                        <textarea name="message" class="form-control" rows="2" placeholder="Type your message here..." required></textarea>
                        <div class="button-group">
                            <button type="submit" name="send" value="send" class="btn btn-primary">
                                <i class="fas fa-robot"></i> Ask AI
                            </button>
                            <button type="submit" name="escalate" value="1" class="btn btn-danger">
                                <i class="fas fa-user-md"></i> Ask Doctor
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
        """
        from django.template import Template, Context
        template = Template(chat_html)
        rendered_html = template.render(Context(context))
        
        return JsonResponse({
            "html": rendered_html,
            "messages": messages_list,
            "status": "success"
        })
        
    return render(request, "patient_chat.html", context)

@login_required
def simulate_all_vitals(request):
    if request.method == "POST":
        user = request.user
        today = timezone.now().date()

        hr = random.randint(60, 150)
        spo2 = random.randint(85, 100)
        temp = round(random.uniform(96.5, 103.0), 1)
        sleep = random.randint(300, 540)

        alert = hr > 130 or hr < 50 or spo2 < 92 or temp > 100.4 or temp < 96.0

        vitals = FitbitVitals.objects.create(
            user=user,
            date=today,
            resting_heart_rate=hr,
            spo2=spo2,
            body_temp=temp,
            sleep_minutes=sleep,
            alert_triggered=alert
        )

        print(f"Simulated: HR={hr}, SpO2={spo2}, Temp={temp}, Sleep={sleep}, Alert={alert}")
        return redirect('patient_dashboard')
    return HttpResponse("Method not allowed", status=405)


"""def simulate_all_vitals(request):
    user = request.user
    today = timezone.now().date()

    FitbitVitals.objects.create(
        user=user,
        date=today,
        resting_heart_rate=random.randint(60, 150),
        spo2=random.randint(85, 100),
        body_temp=round(random.uniform(96.5, 103.0), 1),
        sleep_minutes=random.randint(300, 540),  # optional
        alert_triggered=False  # can update logic later
    )

    return redirect('patient_dashboard') """


### DOCTOR VIEWS ###
@login_required
def patients_list(request):
    """Doctor views all assigned patients & their records."""
    if get_user_role(request.user) != "doctor":
        return redirect('patients_list')

    patients = Patient.objects.all()  # Update this if filtering by assigned doctor
    return render(request, 'patients_list.html', {'patients': patients})

@login_required
def messages_view(request):
    """Doctor sees patient list & full conversation with selected patient."""
    if get_user_role(request.user) != "doctor":
        return redirect('patients_list')

    patients = Patient.objects.all()
    messages_overview = {}

    for patient in patients:
        latest_message = Message.objects.filter(
            Q(sender=patient.user, recipient=request.user) |
            Q(sender=request.user, recipient=patient.user)
        ).order_by('-timestamp').first()

        # Include escalated messages
        """escalated_messages = Message.objects.filter(
            recipient=request.user,
            content__startswith="ESCALATION:"
        ).order_by("-timestamp")"""

        messages_overview[patient] = latest_message

    selected_patient_username = request.GET.get("selected_patient")
    selected_patient = None
    messages_list = None

    if selected_patient_username:
        selected_patient = get_object_or_404(User, username=selected_patient_username)
        messages_list = Message.objects.filter(
            Q(sender=request.user, recipient=selected_patient) | 
            Q(sender=selected_patient, recipient=request.user)
        ).order_by("timestamp")
    
        if request.method == "POST":
            message_content = request.POST.get("message")
            if message_content:
                Message.objects.create(sender=request.user, recipient=selected_patient, content=message_content)
                return redirect(reverse("messages") + f"?selected_patient={selected_patient.username}")   # ✅ Correct

    return render(request, 'messages.html', {
        "patients": patients,
        "messages_overview": messages_overview,
        "selected_patient": selected_patient,
        "messages_list": messages_list,
        #"escalated_messages": escalated_messages,  # ✅ Send escalated messages to template
    })

@login_required
def doctor_dashboard(request):
    if get_user_role(request.user) != "doctor":
        return redirect('home')

    patients = Patient.objects.all()  # Optional: filter by doctor assignment

    data = []
    for patient in patients:
        latest = FitbitVitals.objects.filter(user=patient.user).order_by('-id').first()
        data.append({
            "name": patient.user.get_full_name(),
            "id": patient.id,
            "heart_rate": latest.resting_heart_rate if latest else None,
            "spo2": latest.spo2 if latest else None,
            "temp": latest.body_temp if latest else None,
            "alert": latest.alert_triggered if latest else False,
        })

    return render(request, 'doctor_dashboard.html', {'patients': data})


### ADMIN DASHBOARD ###
@login_required
def admin_dashboard_view(request):
    """Admin can assign roles & view users."""
    if not request.user.is_superuser:
        return redirect('home')

    users = User.objects.all()
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('new_role')
        if user_id and new_role:
            user = get_object_or_404(User, id=user_id)
            group = Group.objects.get(name=new_role)
            user.groups.clear()
            user.groups.add(group)
            messages.success(request, 'Role updated successfully!')
    
    return render(request, 'admin_dashboard.html', {'users': users})

@login_required
def refresh_chat(request):
    """Returns the latest chat messages as JSON for AJAX refresh."""
    messages_list = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).order_by("timestamp")

    messages_data = []
    for msg in messages_list:
        sender_label = msg.sender.username
        role_label = "patient"  # Default role
        content_text = msg.content

        # Determine role and sender based on message content and sender/recipient
        if msg.content.startswith("BOT:"):
            sender_label = "Healthsync Virtual Assistant"
            role_label = "bot"
            content_text = msg.content.replace("BOT: ", "")
        elif msg.content.startswith("PATIENT:"):
            if msg.sender == request.user:
                sender_label = "You"
                role_label = "patient"
            else:
                sender_label = msg.sender.username
                role_label = "patient"
            content_text = msg.content.replace("PATIENT: ", "")
        elif msg.sender.groups.filter(name="Doctor").exists():
            sender_label = f"Dr. {msg.sender.username}"
            role_label = "doctor"

        messages_data.append({
            "sender": sender_label,
            "role": role_label,
            "content": content_text,
            "timestamp": msg.timestamp.strftime("%b %d, %Y %H:%M")
        })

    return JsonResponse({"messages": messages_data})

