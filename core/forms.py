# core/forms.py
from django import forms
from django.contrib.auth.models import User
from notifications.models import Patient, Doctor


class ChatForm(forms.Form):
    message = forms.CharField(label='', widget=forms.TextInput(attrs={
        'placeholder': 'Enter your message here...',
    }))

class PatientRegisterForm(forms.ModelForm):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    phone_number = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password']

class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['phone_number', 'caregiver_phone']

class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['specialty']
        widgets = {
            'is_available_for_call': forms.CheckboxInput()
        }


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']