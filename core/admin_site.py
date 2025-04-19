from django.contrib.admin import AdminSite
from django.urls import reverse, NoReverseMatch
from notifications.models import Appointment

class HealthSyncAdminSite(AdminSite):
    site_header = 'HealthSync Administration'
    site_title = 'HealthSync Admin'
    index_title = 'HealthSync Administration'

    def get_app_list(self, request):
        """
        Return a sorted list of all the installed apps that have been
        registered in this site.
        """
        app_list = super().get_app_list(request)
        
        # Remove only the Patient Records entry if it exists
        for app in app_list:
            if app['app_label'] == 'core':
                app['models'] = [model for model in app['models'] if model['object_name'] != 'PatientRecord']
        
        # Add our custom Medical Records section
        try:
            app_list.append({
                'name': 'Medical Records',
                'app_label': 'medical_records',
                'models': [
                    {
                        'name': 'Patient Records',
                        'object_name': 'patient_records',
                        'admin_url': reverse('admin_patient_list'),
                        'view_only': True,
                    },
                    {
                        'name': 'Appointments',
                        'object_name': 'appointment',
                        'admin_url': reverse('admin:notifications_appointment_changelist'),
                        'view_only': False,
                    }
                ],
            })
        except NoReverseMatch:
            pass
            
        return app_list

    def each_context(self, request):
        context = super().each_context(request)
        context.update({
            'site_header': self.site_header,
            'site_title': self.site_title,
            'index_title': self.index_title,
        })
        return context

admin_site = HealthSyncAdminSite(name='healthsync_admin') 