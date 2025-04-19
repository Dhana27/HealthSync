from django.contrib import admin
from django.utils.html import format_html
from .models import MedicationSchedule, Appointment
from core.admin_site import admin_site

class MedicationScheduleAdmin(admin.ModelAdmin):
    list_display = ('patient', 'medication_name', 'dosage', 'time', 'food_timing', 'duration_days', 'status')
    list_filter = ('food_timing', 'reminder_sent', 'date')
    search_fields = ('patient__user__username', 'medication_name')
    date_hierarchy = 'date'
    
    def status(self, obj):
        if obj.reminder_status == 'taken':
            return format_html('<span style="color: #10b981;">✓ Taken</span>')
        elif obj.reminder_status == 'overdue':
            return format_html('<span style="color: #ef4444;">⚠ Overdue</span>')
        elif obj.reminder_status == 'missed':
            return format_html('<span style="color: #f59e0b;">Missed</span>')
        return format_html('<span style="color: #6b7280;">Pending</span>')
    status.short_description = 'Status'

class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'appointment_date', 'appointment_time', 'status', 'reminder_status')
    search_fields = ('patient__user__username', 'doctor__user__username')
    date_hierarchy = 'appointment_date'
    change_list_template = 'admin/notifications/appointment/change_list.html'
    change_form_template = 'admin/notifications/appointment/change_form.html'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('patient', 'doctor')
    
    def status(self, obj):
        if obj.completed:
            return format_html('<span style="color: #10b981;">✓ Completed</span>')
        return format_html('<span style="color: #2563eb;">Scheduled</span>')
    status.short_description = 'Status'
    
    def reminder_status(self, obj):
        if obj.reminder_sent:
            return format_html('<span style="color: #10b981;">✓ Sent</span>')
        return format_html('<span style="color: #6b7280;">Pending</span>')
    reminder_status.short_description = 'Reminder'

# Register with the custom admin site only
admin_site.register(MedicationSchedule, MedicationScheduleAdmin)
admin_site.register(Appointment, AppointmentAdmin)
