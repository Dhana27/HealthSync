from django import forms
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from notifications.models import Patient, Doctor, Appointment  

# Optional: Mapping for reference if needed.
ROLE_MAP = {
    'Patient': 'patient',
    'Doctor': 'doctor',
    'Admin': 'admin',
}

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user', 'assigned_doctor', 'phone_number', 'caregiver_phone', 'email')
    list_filter = ('assigned_doctor',)
    search_fields = ('user__username', 'email', 'phone_number')
    list_select_related = ('assigned_doctor',)


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialty', 'role')
    search_fields = ('user__username', 'specialty')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'appointment_date', 'appointment_time', 'reminder_sent')
    list_filter = ('appointment_date', 'reminder_sent')
    search_fields = ('patient__user__username', 'doctor__user__username')
    list_select_related = ('patient', 'doctor')

class SingleGroupUserChangeForm(forms.ModelForm):
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label="Group (Role)"
    )

    class Meta:
        model = User
        exclude = ('groups',)  # Exclude the default groups field

    def __init__(self, *args, **kwargs):
        super(SingleGroupUserChangeForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            groups = self.instance.groups.all()
            if groups.exists():
                self.fields['group'].initial = groups.first()
        else:
            self.fields['group'].initial = None

    def save(self, commit=True):
        user = super(SingleGroupUserChangeForm, self).save(commit=False)
        # Store the selected group for use in save_m2m
        self._selected_group = self.cleaned_data.get('group')
        if commit:
            user.save()
            # Clear and assign the selected group immediately if committing now.
            user.groups.clear()
            if self._selected_group:
                user.groups.add(self._selected_group)
        return user

    def save_m2m(self):
        """
        This method will be called by the admin after form.save() if commit was False.
        We override it to ensure our group assignment is applied.
        """
        user = self.instance
        user.groups.clear()
        if self._selected_group:
            user.groups.add(self._selected_group)


# Customized UserAdmin that uses our custom form.
class CustomUserAdmin(BaseUserAdmin):
    form = SingleGroupUserChangeForm
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Group Information', {'fields': ('group',)}),
    )
    list_display = ('username', 'get_group', 'get_group_permissions')

    def get_group(self, instance):
        groups = instance.groups.all()
        if groups.exists():
            return groups.first().name
        return ""
    get_group.short_description = "Group (Role)"

    def get_group_permissions(self, instance):
        groups = instance.groups.all()
        if groups.exists():
            perms = groups.first().permissions.all()
            return ", ".join([perm.name for perm in perms])
        return ""
    get_group_permissions.short_description = "Group Permissions"

    def save_model(self, request, obj, form, change):
        # Save the user object first
        super().save_model(request, obj, form, change)
        # Then update the groups using our custom field value.
        selected_group = form.cleaned_data.get('group')
        obj.groups.clear()
        if selected_group:
            obj.groups.add(selected_group)


# Unregister the default User admin and register our custom one.
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
