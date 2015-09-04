from django.shortcuts import render
from django.http import HttpResponse
import os
from django.conf import settings

import json
import networkx as nx
from networkx.readwrite import json_graph
import threading
import operator
import random
import search
import shelve
import re
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


# TODO limit this to cutoff of 3
def author_search(request):
# TODO deal with names as well as number
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

	nodes = [author_id,]
	neighbours = nx.single_source_shortest_path_length(unigraph, author_id, cutoff)
	
	nodes.extend(neighbours.keys())

	# Making a new subgraph out of the old graph so that changes in attributes are not reflected in full graph
	author_graph = nx.Graph(unigraph.subgraph(nodes))

	author_graph.node[author_id]["centre"] = 1
	for neighbour, hops in neighbours.items():
		author_graph.node[neighbour]["hops"] = hops

	#print author_graph.nodes()
	#print author_graph.edges()

	graphdata = json_graph.node_link_data(author_graph)
	newdata = json.dumps(graphdata)


	return HttpResponse(newdata, content_type='application/json')


def community_viz(request):
	if request.method == 'GET':
		school = request.GET.get("school")
		com_num = int(request.GET.get("com_num"))
		just_school = request.GET.get("just_school")

	print "com num is", com_num
	graphpath = 'collab/' + school + '.json'

	with open(os.path.join(settings.GRAPHS_PATH, graphpath)) as f:
		data = json.load(f)

	school_graph = json_graph.node_link_graph(data)

	if just_school:
		# TODO using .get because not all nodes have school_com key in attributes - maybe add one for everyone, with false if not in school
		com_nodes = [node for node in school_graph.node if school_graph.node[node].get("school_com") == com_num]
	else:
		com_nodes = [node for node in school_graph.node if school_graph.node[node]["com"] == com_num]
	#print "the community is"
	#print com_nodes

	com_graph = school_graph.subgraph(com_nodes)

	# TODO make this into a function, it is repeated in 3 or 4 places
	graphdata = json_graph.node_link_data(com_graph)
	newdata = json.dumps(graphdata)

	return HttpResponse(newdata, content_type='application/json')







def get_unigraph():
	graphpath = os.path.join(settings.GRAPHS_PATH, 'collab/The University of Glasgow.json')
	return graph_utils.graph_from_file(graphpath)

	# with open(os.path.join(settings.GRAPHS_PATH, graphpath)) as f:
	# 	data = json.load(f)

	# unigraph = json_graph.node_link_graph(data)
	# return unigraph


def kw_search(request):
	print "got here"
	if request.method == 'GET':
		query = request.GET.get('query')

	print query
	# TODO make index path
	path = os.path.join(settings.INDICES_PATH + "\invindex10.db")
	#print path
	#akw_path = os.path.join(settings.INDICES_PATH + "\\authorkwindex2.db")
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

	term_graph = nx.Graph()
	unigraph = get_unigraph()

	# TODO factor out networkx stuff from views - pass info to graph making module and get graph in return
	term_graph.add_node(query, {"name":query, "isTerm":True})
	#print "AUTHORS"
	#print author_titles
	# TODO refactor this - sort first by author, then get top 30
	# avoid adding all possible authors to nodes
	# OR change the way authors are returned from search so can easily filter them
	for author_title in author_titles:
		#print "adding node"
		name, authorid = author_title[0]
		#print authorid, name
		title_url = author_title[1]
		#print title_url
		if authorid not in term_graph.node:
			term_graph.add_node(authorid, {"name": name, "paper_count": 1, "school":unigraph.node[authorid]["school"]})
			#print "added node", name
		else:
			term_graph.node[authorid]["paper_count"] += 1

		if term_graph.has_edge(query, authorid):
			term_graph[query][authorid]["num_collabs"] += 1
			term_graph[query][authorid]["weight"] += 1
			term_graph[query][authorid]["collab_title_url_years"].append(title_url)
		else:
			term_graph.add_edge(query, authorid, {"num_collabs":1, "weight":1, "collab_title_url_years": [title_url,]})
	
	if len(term_graph.nodes()) > 30:
		print "TOO MANY NODES"
		nodes_to_sort = [node for node in term_graph.nodes() if node != query]
		sorted_nodes = sorted(nodes_to_sort, key=lambda k: term_graph.node[k]["paper_count"], reverse=True)
		sorted_nodes = sorted_nodes[:29]
		#print sorted_nodes
		sorted_nodes.append(query)
		term_graph = term_graph.subgraph(sorted_nodes)

	graphdata = json_graph.node_link_data(term_graph)
	newdata = json.dumps(graphdata)
	#print "NEWDATA"
	#print newdata

	return HttpResponse(newdata, content_type='application/json')
	#return HttpResponse("")
 

def numerical(info):
	try:
		int(info)
		return True
	except ValueError:
		return False

	


