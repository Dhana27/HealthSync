from django.shortcuts import render
from .models import RecoveryTip

def patient_dashboard(request):
    tips = RecoveryTip.objects.filter(patient=request.user.patient).order_by('-created_at')[:5]
    return render(request, 'dashboard.html', {'tips': tips})
