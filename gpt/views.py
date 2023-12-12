from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from .models import APIKey

def index(request):
    api_key = APIKey.objects.get(id=1)
    context = {"api_key": api_key}
    return render(request, "gpt/index.html", context)