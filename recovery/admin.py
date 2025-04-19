from django.contrib import admin
from django.utils.html import format_html
from .models import RecoveryTip

@admin.register(RecoveryTip)
class RecoveryTipAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'doctor_name', 'created_at', 'advice_preview')
    list_filter = ('created_at', 'doctor')
    search_fields = ('patient__user__username', 'doctor__user__username', 'advice')
    date_hierarchy = 'created_at'
    
    def patient_name(self, obj):
        return f"{obj.patient.user.first_name} {obj.patient.user.last_name}"
    patient_name.short_description = 'Patient'
    
    def doctor_name(self, obj):
        return f"Dr. {obj.doctor.user.first_name} {obj.doctor.user.last_name}"
    doctor_name.short_description = 'Doctor'
    
    def advice_preview(self, obj):
        if len(obj.advice) > 100:
            return format_html('<span title="{}">{}</span>', 
                             obj.advice, 
                             obj.advice[:100] + '...')
        return obj.advice
    advice_preview.short_description = 'Advice'
