from django import forms
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from notifications.models import Patient, Doctor, Appointment, MedicationSchedule
from .models import PatientRecord

admin.site.site_header = 'HealthSync Administration'
admin.site.site_title = 'HealthSync Admin Portal'
admin.site.index_title = 'Welcome to HealthSync Admin Portal'

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

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'assigned_doctor', 'phone_number', 'caregiver_phone', 'email')
    list_filter = ('assigned_doctor', 'user__date_joined')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'email', 'phone_number')
    list_select_related = ('user', 'assigned_doctor')
    inlines = [MedicationInline, PatientRecordInline]
    
    def user_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    user_full_name.short_description = 'Patient Name'

@admin.register(Doctor)
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

@admin.register(PatientRecord)
class PatientRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'created_at', 'diagnosis', 'has_prescription')
    list_filter = ('created_at', 'patient')
    search_fields = ('patient__username', 'symptoms', 'diagnosis')
    date_hierarchy = 'created_at'
    
    def has_prescription(self, obj):
        return bool(obj.prescription)
    has_prescription.boolean = True
    has_prescription.short_description = 'Has Prescription'

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

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
