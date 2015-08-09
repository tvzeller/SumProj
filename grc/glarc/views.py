from django.shortcuts import render
from django.http import HttpResponse
import os
from django.conf import settings
import json
import networkx as nx
from networkx.readwrite import json_graph
import threading

def index(request):
	collab_path = os.path.join(settings.GRAPHS_PATH, "collab")

	collab_graphs = os.listdir(collab_path)
	collab_graphs = [cg.split(".")[0] for cg in collab_graphs]
	context_dict = {"collab_graphs": collab_graphs}
	# Add other graphs to dict when available

	return render(request, 'glarc/index.html', context_dict)

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

def shortest_path(request):
	print "pancakes"
	# TODO doing this with node id's rather than names - ask users to enter enlighten url?
	# would make sure we get the right person
	if request.method == 'GET':
		source_num = request.GET.get('source')
		target_num = request.GET.get('target')

	graphpath = 'collab/The University of Glasgow.json'
	with open(os.path.join(settings.GRAPHS_PATH, graphpath)) as f:
		data = json.load(f)


	unigraph = json_graph.node_link_graph(data)
	# TODO change this - once we start using just number as node ids in graphs
	source_id = "http://eprints.gla.ac.uk/view/author/" + source_num + ".html"
	target_id = "http://eprints.gla.ac.uk/view/author/" + target_num + ".html"
	
	# CHECK IF NODES IN GRAPH
	if source_id not in unigraph.node or target_id not in unigraph.node:
		return HttpResponse({})
	

	try:
		s_path = nx.shortest_path(unigraph, source_id, target_id)
	except nx.NetworkXNoPath:
		return HttpResponse({})
	
	path_graph = nx.Graph()
	for i in range(0, len(s_path)-1):
		author1 = s_path[i]
		author2 = s_path[i+1]
		path_graph.add_node(author1, {"name": unigraph.node[author1]["name"]})
		path_graph.add_node(author2, {"name": unigraph.node[author2]["name"]})
		path_graph.add_edge(author1, author2)


		if author1 == s_path[0]:
			path_graph.node[author1]["isSource"] = 1
		if author2 == s_path[-1]:
			path_graph.node[author2]["isTarget"] = 1

	graphdata = json_graph.node_link_data(path_graph)
	newdata = json.dumps(graphdata)

	print "and got here"

	print threading.active_count()


	return HttpResponse(newdata, content_type='application/json')


def author_search(request):
# TODO deal with names as well as number
	if request.method == 'GET':
		author_num = request.GET.get("author")
		cutoff = int(request.GET.get("cutoff")) 

	print "author_num is",  author_num
	print "cutoff is", cutoff

	graphpath = 'collab/The University of Glasgow.json'
	with open(os.path.join(settings.GRAPHS_PATH, graphpath)) as f:
		data = json.load(f)

	unigraph = json_graph.node_link_graph(data)
	

	author_id = "http://eprints.gla.ac.uk/view/author/" + author_num + ".html"

	if author_id not in unigraph.node:
		return HttpResponse({})

	nodes = [author_id,]
	neighbours = nx.single_source_shortest_path_length(unigraph, author_id, cutoff)
	
	nodes.extend(neighbours.keys())

	print nodes

	# Making a new subgraph out of the old graph so that changes in attributes are not reflected in full graph
	author_graph = nx.Graph(unigraph.subgraph(nodes))
	author_graph.node[author_id]["centre"] = 1
	print author_graph.nodes()
	print author_graph.edges()

	graphdata = json_graph.node_link_data(author_graph)
	newdata = json.dumps(graphdata)


	return HttpResponse(newdata, content_type='application/json')
