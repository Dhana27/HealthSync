from django.urls import path
from .views import (
    manage_patient_health, view_reminders, toggle_availability,
    available_doctors,  request_consultation, my_consult_status,
    doctor_consultation_room, accept_consultation, complete_consult, 
    start_call, check_consult_status, cancel_consultation, 
    create_prescription, view_prescription_pdf, fitbit_logout,
    mark_medication_taken, submit_feedback
    #doctor_messages, chat_detail, join_call,
)

urlpatterns = [
    path("manage_patient_health/<int:patient_id>/", manage_patient_health, name="manage_patient_health"),
    path("view_reminders/", view_reminders, name="view_reminders"),
    path('toggle-availability/', toggle_availability, name='toggle_availability'),
    path('available-doctors/', available_doctors, name='available_doctors'),
    #path('join-call/<int:doctor_id>/', join_call, name='join_call'),
    path('request-consultation/<int:doctor_id>/', request_consultation, name='request_consultation'),

    path('consult/status/<int:consult_id>/', my_consult_status, name='my_consult_status'),
    #path('no-active-consult/', my_consult_status, name='no_active_consult'),
    path('doctor/virtual-consultation/', doctor_consultation_room, name='doctor_consultation_room'),
    path('doctor/accept-consult/<int:consult_id>/', accept_consultation, name='accept_consultation'),

    path('start-call/<int:consult_id>/', start_call, name='start_call'),
    path('check-consult-status/', check_consult_status, name='check_consult_status'),
    path('consult/cancel/<int:consult_id>/', cancel_consultation, name='cancel_consult'),
    path('prescription/create/<int:consult_id>/', create_prescription, name='create_prescription'),
    path('prescription/view/<int:prescription_id>/', view_prescription_pdf, name='view_prescription_pdf'),
    path("complete-consult/<int:consult_id>/", complete_consult, name="complete_consult"),

    path('fitbit/logout/', fitbit_logout, name='fitbit_logout'),

    path('medication/<int:medication_id>/mark-taken/', mark_medication_taken, name='mark_medication_taken'),

    path('submit-feedback/', submit_feedback, name='submit_feedback'),

    #path('generate-token/', generate_100ms_token, name='generate_100ms_token'),

    #path("doctor_messages/", doctor_messages, name="doctor_messages"),
    #path("chat/<int:patient_id>/", chat_detail, name="chat_detail"),
]
