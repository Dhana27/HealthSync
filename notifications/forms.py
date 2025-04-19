from django import forms
from .models import MedicationSchedule, Appointment, MedicalHistory, MedicalHistoryMedication
from recovery.models import RecoveryTip
from django.forms.widgets import DateInput, TimeInput


class MedicationReminderForm(forms.ModelForm):
    class Meta:
        model = MedicationSchedule
        fields = ['medication_name', 'dosage', 'date', 'time', 'duration_days', 'food_timing']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
            'time': TimeInput(attrs={'type': 'time'}),
            'duration_days': forms.NumberInput(attrs={'min': 1}),
        }

class AppointmentReminderForm(forms.ModelForm):
    class Meta:
        model = Appointment
        exclude = ['patient']
        widgets = {
            'appointment_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'appointment_time': TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }

class DietTipForm(forms.ModelForm):
    class Meta:
        model = RecoveryTip
        fields = ['advice']
        widgets = {
            'advice': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class MedicalHistoryForm(forms.ModelForm):
    class Meta:
        model = MedicalHistory
        fields = ['date', 'time', 'diagnosis', 'symptoms']
        widgets = {
            'date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'symptoms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class MedicalHistoryMedicationForm(forms.ModelForm):
    class Meta:
        model = MedicalHistoryMedication
        fields = ['medication_name', 'dosage', 'duration_days', 'food_timing']
        widgets = {
            'duration_days': forms.NumberInput(attrs={'min': 1, 'class': 'form-control'}),
            'medication_name': forms.TextInput(attrs={'class': 'form-control'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control'}),
            'food_timing': forms.Select(attrs={'class': 'form-control'}),
        }
