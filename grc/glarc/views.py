from django.shortcuts import render
from django.http import HttpResponse

def index(request):
	context_dict = {"boldmessage": "hey there"}
	return render(request, 'glarc/index.html', context_dict)

def about(request):
	return HttpResponse("about")
