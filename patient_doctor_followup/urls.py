# patient_doctor_followup/urls.py
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core.admin_site import admin_site

urlpatterns = [
    path('admin/', admin_site.urls),
    path('', include('core.urls')),  # Includes URLs from our core app
    path('notifications/', include('notifications.urls')),
]
