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

	json_file = open(os.path.join(settings.GRAPHS_PATH, "cswithattribs2.json"))
	data = json.dumps(json_file.read())
	json_file.close()

	#data = {'foo': 'bar', 'hello': 'world'}
	
	#print graph_data
	
	return HttpResponse(data, content_type='application/json')

