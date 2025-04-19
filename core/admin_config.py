from django.contrib.admin.apps import AdminConfig


class HealthSyncAdminConfig(AdminConfig):
    default_site = 'core.admin.HealthSyncAdminSite' 