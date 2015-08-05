from django.shortcuts import render
from django.http import HttpResponse
import os
from django.conf import settings
import json

def index(request):
	context_dict = {"boldmessage": "hey there"}
	return render(request, 'glarc/index.html', context_dict)

def about(request):
	return HttpResponse("about")

def get_json(request):
	print "got here"
	print "BLAAAAAAAAA"
	graphname = request.GET.get('name')
	graphtype = request.GET.get('type')
	graphpath = graphtype + '/' + graphname + '.json'

	json_file = open(os.path.join(settings.GRAPHS_PATH, graphpath))
	data = json.dumps(json_file.read())
	json_file.close()

	return HttpResponse(data, content_type='application/json')

