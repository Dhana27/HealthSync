from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "HealthSync"

    def ready(self):
        # Import signals to register them
        #import core.signals # Registers the signal handlers
        pass


class HealthSyncAdminConfig(AdminConfig):
    default_site = "core.admin.HealthSyncAdminSite"