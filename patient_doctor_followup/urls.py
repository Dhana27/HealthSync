# patient_doctor_followup/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),  # Includes URLs from our core app
    path('notifications/', include('notifications.urls')),
]
