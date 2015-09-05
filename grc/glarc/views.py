from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings

import os
import json

import search
import graph_utils

def index(request):
	"""
	Displays the initial page.
	Gets the names of the collaboration graphs and similarity graphs stored in relevant directories
	and passes to the template to be displayed in dropdown menus on page
	"""

	collab_path = os.path.join(settings.GRAPHS_PATH, "collab")

	collab_graphs = os.listdir(collab_path)
	# Get list of just names (without file extension)
	# Full university graph excluded
	collab_graphs = [cg.split(".")[0] for cg in collab_graphs if "University" not in cg]

	sim_path = os.path.join(settings.GRAPHS_PATH, "similarity2")
	sim_graphs = os.listdir(sim_path)
	sim_graphs = [sg.split(".")[0] for sg in sim_graphs]

	context_dict = {"collab_graphs": collab_graphs, "sim_graphs":sim_graphs}

	return render(request, 'glarc/newindex.html', context_dict)


def about(request):
	return render(request, 'glarc/about.html')


def get_json(request):
	"""
	Gets the JSON data for a given graph JSON file and passes to front end
	"""
	if request.method == 'GET':
		graphname = request.GET.get('name')
		graphtype = request.GET.get('type')
	
	graphpath = graphtype + '/' + graphname + '.json'

	json_file = open(os.path.join(settings.GRAPHS_PATH, graphpath))
	data = json.dumps(json_file.read())
	json_file.close()

	return HttpResponse(data, content_type='application/json')


def shortest_path(request):
	"""
	Deals with shortest path request
	"""

	# Get source and target info passed in request
	if request.method == 'GET':
		source_info = request.GET.get('source')
		target_info = request.GET.get('target')

	unigraph = get_unigraph()
	source_id = ""
	target_id = ""
	source_candidates = []
	target_candidates = []
	
	# If source info is a number, it is the node id, set source id to source info
	if numerical(source_info):
		source_id = source_info
	# Otherwise, it is a name - get nodes whose name matches the given name
	else:
		source_candidates = graph_utils.get_matching_nodes(source_info, unigraph)

	# See above
	if numerical(target_info):
		target_id = target_info
	else:
		target_candidates = graph_utils.get_matching_nodes(target_info, unigraph)

	# If both source and target id's are known, return the graph for the path between source and target
	if source_id and target_id:
		return path_graph_from_ids(source_id, target_id, unigraph)

	# Cases where info provided does not match nodes in graph (either source, target or both)
	# In these cases an error message is returned to be displayed in front end
	if len(source_candidates) == 0 and not source_id and len(target_candidates) == 0 and not target_id:
		errorMessage = json.dumps({"error": "Sorry, neither author was found"})
		return HttpResponse(errorMessage, content_type='application/json')
	elif len(source_candidates) == 0 and not source_id:
		errorMessage = json.dumps({"error": "Sorry, the source author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')
	elif len(target_candidates) == 0 and not target_id:
		errorMessage = json.dumps({"error": "Sorry, the target author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')

	# If both source and target have matching nodes
	candidates = {}
	# If there is more than one matching node for source or target, add the candidates to the candidate nodes dict
	# Candidates can then be displayed in front end
	if len(source_candidates) > 1:
		candidates["source_candidates"] = source_candidates
	if len(target_candidates) > 1:
		candidates["target_candidates"] = target_candidates

	# If candidates not empty it means there is more than one candidate for either source or target,
	# return this information to the front end
	if candidates:
		return HttpResponse(json.dumps({"candidates": candidates}), content_type='application/json')

	# Otherwise, there is only one candidate for both source and target, so get their ids
	if not source_id:
		source_id = source_candidates[0]["id"]
	if not target_id:
		target_id = target_candidates[0]["id"]

	# Return the graph for the path between the source and target
	return path_graph_from_ids(source_id, target_id, unigraph)

	
def path_graph_from_ids(source_num, target_num, unigraph):
	"""
	Takes the node ids for source and target and the graph and returns a graph for the path between source and target
	"""

	# Use the ids provided to make urls (which are the actual node ids used in the graph)
	source_id = "http://eprints.gla.ac.uk/view/author/" + source_num + ".html"
	target_id = "http://eprints.gla.ac.uk/view/author/" + target_num + ".html"

	# Get the set of nodes in the graph to check for the source and target
	uni_node_set = graph_utils.get_node_set(unigraph)
	# Check if source and target in graph, if not return error message
	if source_id not in uni_node_set and target_id not in uni_node_set:
		errorMessage = json.dumps({"error": "Sorry, neither author was found"})
		return HttpResponse(errorMessage, content_type='application/json')
	elif source_id not in uni_node_set:
		errorMessage = json.dumps({"error": "Sorry, the source author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')
	elif target_id not in uni_node_set:
		errorMessage = json.dumps({"error": "Sorry, the target author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')		
		
	# If both were found, get the path betwen them
	s_path = graph_utils.get_path(unigraph, source_id, target_id)
	# If s_path is false, no path was found between the authors, return error message
	if not s_path:
		errorMessage = json.dumps({"error": "Sorry, no path was found between the authors"})
		return HttpResponse(errorMessage, content_type='application/json')	
	
	# Otherwise make a graph connecting the path between the authors and return
	path_graph = graph_utils.make_path_graph(s_path, unigraph)

	graphdata = graph_utils.json_from_graph(path_graph)
	newdata = json.dumps(graphdata)

	return HttpResponse(newdata, content_type='application/json')


def longest_path(request):
	"""
	Deals with longest path requests
	"""
	# Get the source info from the request
	if request.method == 'GET':
		source_info = request.GET.get('source')

	unigraph = get_unigraph()

	source_id = ""
	source_candidates = []
	# If source info is a number, it is the node id so return the longest path graph for that node
	if numerical(source_info):
		source_id = source_info
		return longest_from_id(source_id, unigraph)
	# Otherwise info is a name, get nodes which match the name
	else:
		source_candidates = graph_utils.get_matching_nodes(source_info, unigraph)
		
	# If no matching nodes found, return error message
	if len(source_candidates) == 0:
		errorMessage = json.dumps({"error": "Sorry, the source author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')

	candidates = {}
	# If more than one matching node, return the matching nodes to display to user
	if len(source_candidates) > 1:
		candidates["longest_candidates"] = source_candidates
		return HttpResponse(json.dumps({"candidates": candidates}), content_type='application/json')

	# Otherwise only one matching node, return the longest path graph for this node
	source_id = source_candidates[0]["id"]
	
	return longest_from_id(source_id, unigraph)
	

def longest_from_id(source_num, unigraph):
	"""
	Takes the id for a node and a graph and returns a graph of the node's path to its furthest reachable node
	"""
	# Make full node id out of the id number
	source_id = "http://eprints.gla.ac.uk/view/author/" + source_num + ".html"

	# Check if node in graph, if not return error message
	if source_id not in graph_utils.get_node_set(unigraph):
		errorMessage = json.dumps({"error": "Sorry, the author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')	

	# Otherwise get longest path and make and return path graph
	longest_path = graph_utils.get_longest_path(unigraph, source_id)
	path_graph = graph_utils.make_path_graph(longest_path, unigraph)

	graphdata = graph_utils.json_from_graph(path_graph)
	newdata = json.dumps(graphdata)
	return HttpResponse(newdata, content_type='application/json')	


def single_author(request):
	"""
	Deals with single author graph requests
	"""

	# Get author info and cutoff from request
	if request.method == 'GET':
		author_info = request.GET.get("author")
		cutoff = int(request.GET.get("cutoff")) 

	unigraph = get_unigraph()

	# if author info is a number, use it as id and return the graph for that node
	if numerical(author_info):
		author_id = author_info
		return single_from_id(author_id, unigraph, cutoff)
	# Otherwise author info is a name, get nodes matching that name
	else:
		candidates = graph_utils.get_matching_nodes(author_info, unigraph)

	# If no matching nodes, return error message
	if len(candidates) == 0:
		errorMessage = json.dumps({"error": "Sorry, the source author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')

	# If more than one matching node, return matching node information
	if len(candidates) > 1:
		return HttpResponse(json.dumps({"candidates": candidates}), content_type='application/json')

	# Otherwise get id of single match and return graph for that node
	author_id = candidates[0]["id"]
	return single_from_id(author_id, unigraph, cutoff)


def single_from_id(author_num, unigraph, cutoff):
	"""
	Takes node id, full graph and cutoff and returns graph with all nodes reachable by source node up to a distance of cutoff
	"""
	# make full node id
	author_id = "http://eprints.gla.ac.uk/view/author/" + author_num + ".html"
	# Node not found, return error message
	if author_id not in graph_utils.get_node_set(unigraph):
		errorMessage = json.dumps({"error": "Sorry, the author was not found"})
		return HttpResponse(errorMessage, content_type='application/json')

	# Make and return single author graph
	author_graph = graph_utils.single_author_graph(unigraph, author_id, cutoff)

	graphdata = graph_utils.json_from_graph(author_graph)
	newdata = json.dumps(graphdata)

	return HttpResponse(newdata, content_type='application/json')


def get_unigraph():
	"""
	Used to retrieve the full university graph from file
	"""
	graphpath = os.path.join(settings.GRAPHS_PATH, 'collab/The University of Glasgow.json')
	return graph_utils.graph_from_file(graphpath)


def kw_search(request):
	"""
	Deals with keyword searches
	"""
	
	# Get query from request
	if request.method == 'GET':
		query = request.GET.get('query')

	# Paths for the indices
	path = os.path.join(settings.INDICES_PATH + "\invindex10.db")
	tkw_path = os.path.join(settings.INDICES_PATH + "\paperkwindex3.db")
	# Make search object, passing index paths
	srch = search.Search(path, tkw_path)

	# If query in quote marks, do phrase search
	if query[0] == "\"" and query[-1] == "\"":
		query = query[1:-1]
		author_titles = srch.phrase_search(query)

	# If 'OR' in query, it is an OR search
	elif 'OR' in query:
		# Remove the OR so it is not used as a query term
		q = query.replace('OR', '')
		author_titles = srch.or_search(q)

	# Otherwise it is an AND search
	else:
		author_titles = srch.and_search(query)

	unigraph = get_unigraph()

	# Make the query term graph to display in front end and return
	term_graph = graph_utils.make_search_graph(query, author_titles, unigraph, 30)

	graphdata = graph_utils.json_from_graph(term_graph)
	newdata = json.dumps(graphdata)
	
	return HttpResponse(newdata, content_type='application/json')
 

def numerical(info):
	"""
	Function to check whether a string is numerical
	"""
	try:
		int(info)
		return True
	except ValueError:
		return False

	


