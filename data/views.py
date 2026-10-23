from django.shortcuts import render
from .models import mps

# Create your views here.
def mps_list(request):
    data_mps = mps.objects.all()
    return render(request,'mps_list.html', {'data_mps'= data_mps})