from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from .models import APIKey, Prompt


from django.contrib.auth.decorators import login_required
@login_required
def index(request):
    api_key = APIKey.objects.get(id=1)
    prompts = Prompt.objects.filter(active=True)
    context = {"api_key": api_key, "prompts": prompts}
    return render(request, "gpt/index.html", context)


