from django.urls import path
from .views import (
    home_view, login_view, logout_view, 
    patient_chat_view, patients_list, messages_view, 
    admin_dashboard_view, refresh_chat, fitbit_login, 
    fitbit_callback, simulate_all_vitals, patient_dashboard_view,
    doctor_dashboard, edit_patient_profile, register_patient,
    edit_doctor_profile
)
#from . import views

urlpatterns = [
    path("", home_view, name="home"),
    path("login/", login_view, name="login"),
    path('register/', register_patient, name='register_patient'),
    path("logout/", logout_view, name="logout"),
    path("patient_chat/", patient_chat_view, name="patient_chat"),
    path("patients/", patients_list, name="patients_list"),
    path("messages/", messages_view, name="messages"),
    path("admin_dashboard/", admin_dashboard_view, name="admin_dashboard"),
    path("refresh_chat/", refresh_chat, name="refresh_chat"),
    #path("get_conversation/", get_conversation, name="get_conversation"),
    path('fitbit/login/', fitbit_login, name='fitbit_login'),
    path('fitbit/callback/', fitbit_callback, name='fitbit_callback'),
    #path("simulate-vitals/", simulate_vitals, name="simulate_vitals"),
    path("patient_dashboard/", patient_dashboard_view, name="patient_dashboard"),
    path('simulate-all-vitals/', simulate_all_vitals, name='simulate_all_vitals'),
    path('doctor-dashboard/', doctor_dashboard, name='doctor_dashboard'),
    path('edit-profile/', edit_patient_profile, name='edit_patient_profile'),
    path('edit-doctor-profile/', edit_doctor_profile, name='edit_doctor_profile'),


]
