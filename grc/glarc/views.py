from django.shortcuts import render
from django.http import HttpResponse
import os
from django.conf import settings

import json

#import threading
#import operator
import random
import search
#import shelve
#import re
import graph_utils

def index(request):
	collab_path = os.path.join(settings.GRAPHS_PATH, "collab")

	collab_graphs = os.listdir(collab_path)
	collab_graphs = [cg.split(".")[0] for cg in collab_graphs if "University" not in cg]

	sim_path = os.path.join(settings.GRAPHS_PATH, "similarity2")
	sim_graphs = os.listdir(sim_path)
	sim_graphs = [sg.split(".")[0] for sg in sim_graphs]

	context_dict = {"collab_graphs": collab_graphs, "sim_graphs":sim_graphs}
	# Add other graphs to dict when available

	return render(request, 'glarc/newindex.html', context_dict)




def about(request):
	return render(request, 'glarc/about.html')

# TODO what if json file not found? Display error message
def get_json(request):
	if request.method == 'GET':
		graphname = request.GET.get('name')
		graphtype = request.GET.get('type')
	
	graphpath = graphtype + '/' + graphname + '.json'

	json_file = open(os.path.join(settings.GRAPHS_PATH, graphpath))
	data = json.dumps(json_file.read())
	json_file.close()

	return HttpResponse(data, content_type='application/json')


def shortest_path(request):
	# TODO doing this with node id's rather than names - ask users to enter enlighten url?
	# would make sure we get the right person
	if request.method == 'GET':
		source_info = request.GET.get('source')
		target_info = request.GET.get('target')

	unigraph = get_unigraph()
	source_id = ""
	target_id = ""
	source_candidates = []
	target_candidates = []
	if numerical(source_info):
		source_id = source_info
	else:
		source_candidates = graph_utils.get_matching_nodes(source_info, unigraph)

	if numerical(target_info):
		target_id = target_info
	else:
		target_candidates = graph_utils.get_matching_nodes(target_info, unigraph)

	if source_id and target_id:
		return path_graph_from_ids(source_id, target_id, unigraph)

	
	if len(source_candidates) == 0 and not source_id and len(target_candidates) == 0 and not target_id:
		errorMessage = json.dumps({"error": "Sorry, neither author was found"})
		return HttpResponse(errorMessage, content_type='application/json')
	elif len(source_candidates) == 0 and not source_id:
		errorMessage = json.dumps({"error": "Sorry, the source author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')
	elif len(target_candidates) == 0 and not target_id:
		errorMessage = json.dumps({"error": "Sorry, the target author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')

	candidates = {}
	if len(source_candidates) > 1:
		candidates["source_candidates"] = source_candidates
	if len(target_candidates) > 1:
		candidates["target_candidates"] = target_candidates

	print "PAST adding to candidates"

	if candidates:
		print candidates
		return HttpResponse(json.dumps({"candidates": candidates}), content_type='application/json')

	print "past all that"
	#print source_candidates[0][1], target_candidates[0][1]
	if not source_id:
		print "don't have source id"
		print source_candidates
		source_id = source_candidates[0]["id"]
	if not target_id:
		target_id = target_candidates[0]["id"]

	print "got past assigning ids"

	# At this point we know we have just one matching author for source and target
	return path_graph_from_ids(source_id, target_id, unigraph)
	
def path_graph_from_ids(source_num, target_num, unigraph):
	print "GETTING TO PATH GRAPH FROM"
	# TODO change this - once we start using just number as node ids in graphs
	source_id = "http://eprints.gla.ac.uk/view/author/" + source_num + ".html"
	target_id = "http://eprints.gla.ac.uk/view/author/" + target_num + ".html"

	# CHECK IF NODES IN GRAPH
	uni_node_set = graph_utils.get_node_set(unigraph)
	if source_id not in uni_node_set and target_id not in uni_node_set:
		errorMessage = json.dumps({"error": "Sorry, neither author was found"})
		return HttpResponse(errorMessage, content_type='application/json')
	elif source_id not in uni_node_set:
		errorMessage = json.dumps({"error": "Sorry, the source author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')
	elif target_id not in uni_node_set:
		errorMessage = json.dumps({"error": "Sorry, the target author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')		
		
	s_path = graph_utils.get_path(unigraph, source_id, target_id)
	if not s_path:
		errorMessage = json.dumps({"error": "Sorry, no path was found between the authors"})
		return HttpResponse(errorMessage, content_type='application/json')	
	
	path_graph = graph_utils.make_path_graph(s_path, unigraph)

	graphdata = graph_utils.json_from_graph(path_graph)
	newdata = json.dumps(graphdata)

	return HttpResponse(newdata, content_type='application/json')


def longest_path(request):
	if request.method == 'GET':
		source_info = request.GET.get('source')

	unigraph = get_unigraph()

	source_id = ""
	source_candidates = []
	if numerical(source_info):
		source_id = source_info
		return longest_from_id(source_id, unigraph)
	else:
		source_candidates = graph_utils.get_matching_nodes(source_info, unigraph)
		
	
	if len(source_candidates) == 0:
		errorMessage = json.dumps({"error": "Sorry, the source author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')

	candidates = {}
	if len(source_candidates) > 1:
		candidates["longest_candidates"] = source_candidates
		return HttpResponse(json.dumps({"candidates": candidates}), content_type='application/json')

	source_id = source_candidates[0]["id"]
	
	return longest_from_id(source_id, unigraph)
	

def longest_from_id(source_num, unigraph):
	source_id = "http://eprints.gla.ac.uk/view/author/" + source_num + ".html"
	print source_id

	if source_id not in graph_utils.get_node_set(unigraph):
		errorMessage = json.dumps({"error": "Sorry, the author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')	

	longest_path = graph_utils.get_longest_path(unigraph, source_id)
	path_graph = graph_utils.make_path_graph(longest_path, unigraph)

	graphdata = graph_utils.json_from_graph(path_graph)
	newdata = json.dumps(graphdata)
	return HttpResponse(newdata, content_type='application/json')	


def single_author(request):
	if request.method == 'GET':
		author_info = request.GET.get("author")
		cutoff = int(request.GET.get("cutoff")) 

	#print "author_num is",  author_num
	print "cutoff is", cutoff

	unigraph = get_unigraph()

	if numerical(author_info):
		author_id = author_info
		return single_from_id(author_id, unigraph, cutoff)
	#author_id = "http://eprints.gla.ac.uk/view/author/" + author_num + ".html"
	else:
		candidates = graph_utils.get_matching_nodes(author_info, unigraph)

	if len(candidates) == 0:
		errorMessage = json.dumps({"error": "Sorry, the source author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')

	if len(candidates) > 1:
		return HttpResponse(json.dumps({"candidates": candidates}), content_type='application/json')

	author_id = candidates[0]["id"]
	return single_from_id(author_id, unigraph, cutoff)



def single_from_id(author_num, unigraph, cutoff):
	# TODO change once using just id instead of url
	author_id = "http://eprints.gla.ac.uk/view/author/" + author_num + ".html"

	if author_id not in graph_utils.get_node_set(unigraph):
		errorMessage = json.dumps({"error": "Sorry, the author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')

	author_graph = graph_utils.single_author_graph(unigraph, author_id, cutoff)

	graphdata = graph_utils.json_from_graph(author_graph)
	newdata = json.dumps(graphdata)

	return HttpResponse(newdata, content_type='application/json')


def get_unigraph():
	graphpath = os.path.join(settings.GRAPHS_PATH, 'collab/The University of Glasgow.json')
	return graph_utils.graph_from_file(graphpath)


def kw_search(request):
	print "got here"
	if request.method == 'GET':
		query = request.GET.get('query')

	print query
	path = os.path.join(settings.INDICES_PATH + "\invindex10.db")
	tkw_path = os.path.join(settings.INDICES_PATH + "\paperkwindex3.db")

	srch = search.Search(path, tkw_path)

	if query[0] == "\"" and query[-1] == "\"":
		query = query[1:-1]
		author_titles = srch.phrase_search(query)

	# TODO make AND search the default, with OR as an option
	elif 'OR' in query:
		q = query.replace('OR', '')
		author_titles = srch.or_search(q)
		#print author_titles

	else:
		author_titles = srch.and_search(query)
		print "GOT HERE"
		#print author_titles

	unigraph = get_unigraph()

	term_graph = graph_utils.make_search_graph(query, author_titles, unigraph, 30)

	graphdata = graph_utils.json_from_graph(term_graph)
	newdata = json.dumps(graphdata)
	
	return HttpResponse(newdata, content_type='application/json')
	#return HttpResponse("")
 

def numerical(info):
	try:
		int(info)
		return True
	except ValueError:
		return False

	


