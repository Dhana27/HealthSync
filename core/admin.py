from django import forms
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin
from django.utils.html import format_html
from notifications.models import Patient, Doctor, Appointment, MedicationSchedule
from .models import PatientRecord, FitbitVitals
from django.urls import reverse
from .admin_site import admin_site
from django.shortcuts import redirect

class MedicationInline(admin.TabularInline):
    model = MedicationSchedule
    extra = 0
    fields = ('medication_name', 'dosage', 'time', 'food_timing', 'duration_days')
    can_delete = True

class PatientRecordInline(admin.TabularInline):
    model = PatientRecord
    extra = 0
    fields = ('symptoms', 'diagnosis', 'prescription', 'created_at')
    readonly_fields = ('created_at',)
    can_delete = True

class PatientAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'get_email', 'created_at', 'view_medical_history')
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Patient Name'
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    
    def created_at(self, obj):
        return obj.user.date_joined
    created_at.short_description = 'Created At'
    
    def view_medical_history(self, obj):
        url = reverse('admin_medical_history', args=[obj.id])
        return format_html('<a class="button" href="{}">View Medical History</a>', url)
    view_medical_history.short_description = 'Medical History'

class DoctorAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'specialty', 'role', 'patient_count', 'upcoming_appointments')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'specialty')
    list_filter = ('specialty', 'role')
    
    def user_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    user_full_name.short_description = 'Doctor Name'
    
    def patient_count(self, obj):
        return Patient.objects.filter(assigned_doctor=obj).count()
    patient_count.short_description = 'Number of Patients'
    
    def upcoming_appointments(self, obj):
        count = Appointment.objects.filter(doctor=obj, completed=False).count()
        return format_html('<span style="color: #2563eb;">{}</span>', count)
    upcoming_appointments.short_description = 'Pending Appointments'

class PatientRecordAdmin(admin.ModelAdmin):
    list_display = ('get_patient_name', 'created_at', 'get_last_appointment')
    search_fields = ('patient__user__username', 'patient__user__first_name', 'patient__user__last_name')
    ordering = ('-created_at',)
    
    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name() or obj.patient.user.username
    get_patient_name.short_description = 'Patient Name'
    
    def get_last_appointment(self, obj):
        last_appointment = Appointment.objects.filter(patient=obj.patient.user).order_by('-date').first()
        if last_appointment:
            return last_appointment.date
        return None
    get_last_appointment.short_description = 'Last Appointment'

    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        return redirect('/notifications/admin/patients/')  # Redirect to our custom view

class SingleGroupUserChangeForm(forms.ModelForm):
    group = forms.ModelChoiceField(queryset=Group.objects.all(), required=False)

    class Meta:
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['group'] = self.instance.groups.first()

class CustomUserAdmin(BaseUserAdmin):
    form = SingleGroupUserChangeForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_active', 'date_joined')
    list_filter = ('is_active', 'groups', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'first_name', 'last_name', 'groups'),
        }),
    )
    
    def get_role(self, obj):
        if obj.groups.filter(name='Doctor').exists():
            return 'Doctor'
        elif obj.groups.filter(name='Patient').exists():
            return 'Patient'
        return 'Admin'
    get_role.short_description = 'Role'
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if 'group' in form.cleaned_data:
            group = form.cleaned_data['group']
            if group:
                obj.groups.clear()
                obj.groups.add(group)

# Register models with our custom admin site
admin_site.register(Group, GroupAdmin)
admin_site.register(Patient, PatientAdmin)
admin_site.register(Doctor, DoctorAdmin)
admin_site.register(PatientRecord, PatientRecordAdmin)
admin_site.register(User, CustomUserAdmin)
admin_site.register(FitbitVitals)
