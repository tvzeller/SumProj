from django.shortcuts import render
from django.http import HttpResponse
import os
from django.conf import settings
import json

def index(request):
	return render(request, 'glarc/index.html')

def about(request):
	return HttpResponse("about")

# TODO what if json file not found? Display error message
def get_json(request):
	print "got here"
	print "BLAAAAAAAAA"
	if request.method == 'GET':
		graphname = request.GET.get('name')
		graphtype = request.GET.get('type')
	
	graphpath = graphtype + '/' + graphname + '.json'

	json_file = open(os.path.join(settings.GRAPHS_PATH, graphpath))
	data = json.dumps(json_file.read())
	json_file.close()

	return HttpResponse(data, content_type='application/json')

