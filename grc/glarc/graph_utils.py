# Module to deal with the creation of graphs and graph analysis.
# Used by data_processor and also within the Django views, to create shortest path and
# single author graphs on demand.

import networkx as nx
from networkx.readwrite import json_graph
import json
import tfidf
import time
import community
import operator
import text_utils as tu
import re
import random

class CollabGraphMaker(object):
	"""
	Class to deal with creating collaboration graphs from data provided
	"""

	def __init__(self, g=None):
		self.schl_name_urls = []
		if g==None:
			self.graph = nx.Graph()
		else:
			self.graph = g


	def populate_graph(self, data_dict, snurls):
		"""
		Adds nodes and edges to graph based on information in data_dict.
		snurls is a list of (name, enlighten urls) of authors in the relevant school, used
		to check if a node in the graph is a member of the school or not (this info is added as a node attribute)
		"""
		self.schl_name_urls = snurls

		for paper_id, info in data_dict.items():
			title = info["title"]
			authors = info["authors"]
			if not authors:
				continue
			
			# Add a vertex in graph for each author
			for author in authors:
				self.add_vertex(author)
			
			paper_url = info['url']
			paper_year = info['year']
			# Add links between coauthors
			self.add_links(title, paper_url, paper_year, authors)

	def add_vertex(self, author):
		"""
		Takes author info and adds author as a vertex in the graph
		"""

		# author may be either a (name, unique_url) pair or just a name string (if data comes from enlighten_scraper they are (name, urls))
		# If just a string, the name is used as both the node identifier and the "name" attribute
		# Otherwise access the (name, url) collection to get the url (to use as id) and the author name
		if isinstance(author, basestring):
			vertex_id = author
			name = author
		else:
			vertex_id = author[1]
			name = author[0]

		if vertex_id in self.graph.node:
			# Vertex already exists, increase the paper count attribute
			self.graph.node[vertex_id]["paper_count"] += 1
		else:
			# New vertex
			self.graph.add_node(vertex_id, {"name": name, "paper_count": 1})
			in_school = self.check_schl_status(vertex_id)
			# G.node returns {node: {attributes}} dictionary, can use this to set new attributes after node is created
			self.graph.node[vertex_id]["in_school"] = in_school

	def add_links(self, title, url, year, authors):
		"""
		Adds links between each author in given list of authors. Takes title, url and year of paper to add as link attributes.
		"""
		# Check if authors is a list of collections or just strings
		# If collections, make new list out of element at index 1, which is the unique author url and the node id
		if not isinstance(authors[0], basestring):
			authors = [author[1] for author in authors]

		num_authors = len(authors)
		for i in range(0, num_authors):
			for j in range(i+1, num_authors):
				author1 = authors[i]
				author2 = authors[j]
				# Check if edge already exists, if so update edge attributes
				if self.graph.has_edge(author1, author2):
					# weight is the inverse of the total number of coauthors for the paper, so the weight of a collaboration
					# with several other authors will be less (authors will likely have worked less closely together)
					self.graph[author1][author2]["weight"] += 1.0 / num_authors
					self.graph[author1][author2]["num_collabs"] += 1
					self.graph[author1][author2]["collab_title_url_years"].append([title, url, year])
				# If edge is new, add it to the graph, give it initial attributes
				else:
					self.graph.add_edge(author1, author2, {'weight': 1.0 / num_authors, "num_collabs": 1, "collab_title_url_years": [[title, url, year],]})


	def check_schl_status(self, author_id):
		"""
		Takes author id and checks if author is in the school to which this graph corresponds
		"""		
		if self.schl_name_urls:
			for name_url in self.schl_name_urls:
				if author_id in name_url:
					return True 
			
			return False 

		# If no list of names of school members has been provided (e.g. when data comes from OAI) return false
		else:
			return False


	def get_graph(self):
		"""
		Returns the graph
		"""
		return self.graph


####End of class#####


def write_to_file(g, path):
	"""
	Used to write the graph to a JSON file.
	Serialises to JSON using NetworkX's node_link_data function.
	"""
	graph_data = json_graph.node_link_data(g)
	with open(path, 'w') as f:
		json.dump(graph_data, f)


def add_metrics(g):
	"""
	Adds centrality metrics and community number attributes to each node in the given graph.
	Returns the graph with new node attributes.
	"""
	# Each function returns a dict keyed by node id with the computed metric as value
	deg_cent = nx.degree_centrality(g)
	close_cent = nx.closeness_centrality(g)
	between_cent = nx.betweenness_centrality(g)
	com = community.best_partition(g)
	# Only interested in communities with more than one member - get a list
	# of multimember communities, sorted by community number
	sorted_coms = get_sorted_multimember_coms(com)

	# Loop through nodes in the graph and give them new attributes
	for vertex in self.graph.node.keys():
		g.node[vertex]["deg_cent"] = deg_cent[vertex]
		g.node[vertex]["close_cent"] = close_cent[vertex]
		g.node[vertex]["between_cent"] = between_cent[vertex]

		# Only nodes in a multimember community get a community number
		if com[vertex] in sorted_coms:
			# So community numbers start at 1, change community numbers to their position in the sorted_coms
			# list, plus 1
			# e.g. first multimember community number may be 3, this makes it 0 (position in list) + 1
			new_com_num = sorted_coms.index(com[vertex]) + 1
			g.node[vertex]["com"] = new_com_num
		# If node not in a multimember community, gets False as com number attribute
		else:
			g.node[vertex]["com"] = False

	return g

def add_just_school_community(g):
	"""
	Computes communities based on the subgraph containing just nodes that are members of the school which the
	graph represents, and adds as node attributes.
	Returns graph with new node attributes.
	"""
	# Get just the members of the school
	school_nodes = [node for node in g.node if g.node[node].get("in_school")]
	# Create subgraph from subset of nodes
	just_school_graph = g.subgraph(school_nodes)
	# Get node:com_number dict based on subgraph
	com = community.best_partition(just_school_graph)
	# Get just the multimember communities
	sorted_coms = get_sorted_multimember_coms(com)

	for vertex in just_school_graph.node.keys():
		if com[vertex] in sorted_coms:
			new_com_num = sorted_coms.index(com[vertex]) + 1
			g.node[vertex]["school_com"] = new_com_num
		else:
			g.node[vertex]["school_com"] = False

	return g


def get_sorted_multimember_coms(com_dict):
	"""
	Takes a {node:comnumber} dict and returns a list of just the communities with more
	than one member, sorted by community number 
	"""
	# Set to hold communities with more than one member
	multimember_coms = set()
	for comnum in com_dict.values():
		# Check if community occurs more than once in comdict values
		if com_dict.values().count(comnum) > 1:
			# If so, has more than one member, add to set
			multimember_coms.add(comnum)

	# Sort set by com number (making it a list) and return
	sorted_coms = sorted(multimember_coms)
	return sorted_coms


def add_school_info(school_graphs, school_urls):
	"""
	Takes two dicts - {school name: school collab_graph} and {school name: list of school urls} (where the school urls is a list of the urls
	of the authors in that school) and adds the name of the author's school to each author's node as an attribute. If author not found in any
	school's urls, gets False as a school attribute.
	Returns {school: graph} dict with changed graphs
	"""
	# Loop through each node in each graph
	for schl, graph in school_graphs.items():
		for author in graph.nodes():
			found = False
			# node id is a url. Look for node id in urls of each school.
			for school, urls in school_urls.items():
				if author in urls:
					# Once found, set node's school to that school and break
					found = True
					graph.node[author]['school'] = school
					break

			# Author not found in any school urls, set school to False
			if not found:
				g.node[author]['school'] = False

		school_graphs[schl] = graph

	return school_graphs

def make_unigraph(all_graphs):
	"""
	Makes the collaboration graph for the full university, by composing the given list of all the school graphs.
	Returns full university graph
	"""
	unigraph = nx.compose_all(all_graphs)
	unigraph = add_metrics(unigraph)
	return unigraph

def make_interschool_graph(schoolnames, unigraph):
	"""
	Takes list of school names and full uni graph and makes graph where nodes are schools with links between them if
	authors from those schools have coauthored a paper
	Returns interschool graph
	"""

	interschool_graph = nx.Graph(graphname="SchoolsGraph")

	for schoolname in schoolnames:
		# NB node gets school name as id, but we are giving it a name attribute as well to work better with the javascript code
		interschool_graph.add_node(schoolname, {"name":schoolname})

	# Iterate through each edge (pair of coauthors) in full university graph
	for edge in unigraph.edges():
		# Get the schools of both authors
		school1 = unigraph.node[edge[0]]['school']
		school2 = unigraph.node[edge[1]]['school']

		# Check if they are from different schools
		# Attention author may have school attribute as false if not associated to any school
		if school1 == school2 or school1 == False or school2 == False:
			continue
		
		# Get the edge attributes for the co-author edge
		edgeattribs = unigraph[edge[0]][edge[1]]
		# Check if interschool graph already has edge between the 2 schools
		if interschool_graph.has_edge(school1, school2):
			# Check if papers are already in title_urls to avoid repetition
			for title_url in edgeattribs["collab_title_url_years"]:
				if title_url not in schools_graph[school1][school2]["collab_title_url_years"]:
					interschool_graph[school1][school2]["weight"] += 1
					interschool_graph[school1][school2]["num_collabs"] += 1
					interschool_graph[school1][school2]["collab_title_url_years"].append(title_url)

		# New interschool edge
		else:
			interschool_graph.add_edge(school1, school2, {
													"num_collabs": edgeattribs["num_collabs"], 
													"weight": edgeattribs["num_collabs"],
													"collab_title_url_years": edgeattribs["collab_title_url_years"]})


	schools_graph = add_metrics(schools_graph)
	
	return interschool_graph



def add_com_keywords(akw, g):
	"""
	Takes a school collaboration graph and an {author: author keywords} dict, gives keywords
	to each community in the graph and adds this info as a graph attribute.
	Does this for communities computed from full school graph and communities computed from
	subgraph containing just school members
	"""
	com_keywords = {}
	school_com_keywords = {}

	for author in akw:
		keywords = akw[author]["keywords"]
		com_num = g.node[author]["com"]
		# Use get as author may not have school_com
		school_com_num = g.node[author].get("school_com")
		# (com_num may be false)
		if com_num and com_num not in com_keywords:
			com_keywords[com_num] = keywords
		elif com_num in com_keywords:
			com_keywords[com_num].extend(keywords)

		if school_com_num and school_com_num not in school_com_keywords:
			school_com_keywords[school_com_num] = keywords
		elif school_com_num in school_com_keywords:
			school_com_keywords[school_com_num].extend(keywords)

	g = assign_com_keywords(com_keywords, 'com_keywords')
	g = assign_com_keywords(school_com_keywords, 'school_com_keywords')

	return g


def assign_com_keywords(g, comkwdict, attr_name):
	"""
	Takes a graph, a {community number: keywords} dict and the name of the graph attribute to add and adds
	the attribute to the graph
	"""

	g.graph[attr_name] = []
	for com, keywords in comkwdict.items():
		# Get the top keywords for this community
		top_com_words = tu.get_most_frequent(keywords, 20)
		
		# Add this community's keywords to list of (com_num, keywords) pairs in graph attribute		
		if attr_name in self.graph.graph: 
			g.graph[attr_name].append([com, top_com_words])
		else:
			g.graph[attr_name] = [[com, top_com_words],]

	return g


def make_sim_graph(akw, col_graph):
	"""
	Takes an {author: author keywords} dict and the collaboration graph for a school and creates a graph
	where the nodes are authors linked if their keywords are similar.
	Returns the similarity graph
	"""

	sim_graph = nx.Graph()
	sim_threshold = 0.2

	authors = akw.keys()
	values = akw.values()

	for i in range (0, len(authors)):
		author1 = authors[i]
		# make keywords into set to remove duplicates then back into list to maintain order
		keywords = list(set(values[i]["keywords"]))
		# Add the author to the similarity graph
		add_sim_graph_node(author1, keywords, sim_graph, col_graph)
		# Get a stemmed version of the author's keywords
		stemmed1 = (tu.stem_word_list(keywords[:]))

		# Compare author against each other author in graph
		for j in range(i+1, len(authors)):
			author2 = authors[j]
			keywords2 = list(set(values[j]["keywords"]))
			add_sim_graph_node(author2, keywords2, sim_graph, col_graph)
		
			stemmed2 = (tu.stem_word_list(keywords2[:]))

			# Check similarity of keywords
			sim = tu.check_kw_sim(stemmed1, stemmed2)
			# the similarity score
			ratio = sim[0]
			# the indices (in the longest of the two author keyword lists) of the keywords that are similar
			indices = sim[1]
			matched_words = []

			if len(keywords) > len(keywords2):
				longest = keywords
			else:
				longest = keywords2

			# Get the keywords in the indices returned from check_sim
			for i in indices:
				matched_words.append(longest[i])

			# If similarity score greater than threshold, add edge between authors
			if ratio > sim_threshold:
				sim_graph.add_edge(author1, author2, {"num_collabs":ratio, "sim_kw": matched_words})
				# Indicate whether authors are actual coauthors
				if col_graph.has_edge(author1, author2):
					sim_graph[author1][author2]["areCoauthors"] = True

	return sim_graph

def add_sim_graph_node(node_id, keywords, sim_graph, col_graph):
	"""
	Adds a node to similarity graph, using some of the attributes the node has in the collaboration graph
	"""
	sim_graph.add_node(node_id, {
									"name": col_graph.node[node_id]["name"], 
									"in_school":col_graph.node[node_id]["in_school"],
									"paper_count":col_graph.node[node_id]["paper_count"],
									"keywords":keywords
									})


def graph_from_file(path):
	"""
	Given a file path, makes a NetworkX graph from the JSON data and returns
	"""
	with open(path) as f:
		data = json.load(f)

	g = json_graph.node_link_graph(data)
	return g

def get_matching_nodes(name, graph):
	"""
	Takes an author name and returns a list of the nodes in the graph whose name attribute matches the given name
	"""
	matching_nodes = []
	for nodeid in graph.node:
		# Check if queried name is contained in node's name attribute
		if name in graph.node[nodeid]["name"].lower():
			# If so, get the simplified id (just the number) from the full node id (a url)
			simpleid = re.search("[0-9]+", nodeid).group()
			# Add info dict to matching nodes list
			matching_nodes.append({"name": graph.node[nodeid]["name"], "id": simpleid, "school": graph.node[nodeid]["school"]})

	return matching_nodes

def get_node_set(g):
	"""
	Given a graph, returns the set of nodes in the graph
	"""
	return set(g.nodes())

def get_path(g, source, target):
	"""
	Given a graph and source and target nodes, returns a list of nodes that make up the shortest path between source and target
	"""
	try:
		s_path = nx.shortest_path(g, source, target)
		return s_path
	except nx.NetworkXNoPath:
		return False

def make_path_graph(path, full_graph):
	"""
	Given a list of nodes in a node to node path and the corresponding full graph, makes and returns a path graph
	"""
	path_graph = nx.Graph()
	# Check if path is longer than 1 - author may not have any collaborators
	if len(path) > 1:
		for i in range(0, len(path)-1):
			author1 = path[i]
			author2 = path[i+1]
			# Give the nodes and edges the relevant attributes taken from the full graph
			path_graph.add_node(author1, {"name": full_graph.node[author1]["name"], "school": full_graph.node[author1]["school"]})
			path_graph.add_node(author2, {"name": full_graph.node[author2]["name"], "school": full_graph.node[author2]["school"]})
			path_graph.add_edge(author1, author2, {
													"num_collabs": full_graph[author1][author2]["num_collabs"],
													"collab_title_url_years": full_graph[author1][author2]["collab_title_url_years"]})

			# Mark the source and target nodes within the path graph
			if author1 == path[0]:
				path_graph.node[author1]["isSource"] = 1
			if author2 == path[-1]:
				path_graph.node[author2]["isTarget"] = 1
	
	# For cases where node has no collaborators and path is a single node
	elif len(path) == 1:
		author = path[0]
		path_graph.add_node(author, {
									"name": full_graph.node[author]["name"], 
									"school": full_graph.node[author]["school"],
									"isSource": 1,
									"isTarget": 1})
	
	return path_graph


def json_from_graph(g):
	"""
	Given a graph, returns the JSON data for the graph (which can be passed to JavaScript for D3 graph visualisation)
	"""
	return json_graph.node_link_data(g)


def get_longest_path(g, source):
	"""
	Given a graph and a source node, returns a list of nodes comprising a path from the source to the furthest reachable node.
	There may be several of these so this chooses one of them randomly.
	"""
	# Gets a {target node: path from source} dict
	paths = nx.single_source_shortest_path(g, source)
	path_len = {}
	# Make a dict keyed by target node with the length of the path to it as a value
	for target, path in paths.items():
		path_len[target] = len(path)

	# Get the targets with the longest path away from the source author
	furthest_targets = [target for target in path_len.keys() if path_len[target] == max(path_len.values())]
	# Choose a random furthest target
	chosen_target = random.choice(furthest_targets)
	# Get the path from the source to the chosen target
	longest_path = paths[chosen_target]

	return longest_path


def single_author_graph(full_graph, author, cutoff):
	"""
	Given a graph, a node and maximum distance, makes a subgraph made up of the nodes reachable by the central node,
	up to the maximum distance
	"""
	nodes = [author,]
	# Gets a dict where the keys are the target nodes and the values are the distance from the source node,
	# only including target nodes up the maximum distance away
	neighbours = nx.single_source_shortest_path_length(full_graph, author, cutoff)
	
	# Add the target nodes to the list of nodes
	nodes.extend(neighbours.keys())
	# Making a new subgraph out of the old graph so that changes in attributes are not reflected in full graph
	author_graph = nx.Graph(full_graph.subgraph(nodes))

	# Mark the source node
	author_graph.node[author]["centre"] = 1
	# Add the distance from the source node as a node attribute for each other node
	for neighbour, hops in neighbours.items():
		author_graph.node[neighbour]["hops"] = hops

	return author_graph


def make_search_graph(query, results, full_graph, max_authors):
	"""
	Takes:
	a query term
	a dict where the keys are authors and the values are lists of papers (the results of searching for the query)
	the full graph where the authors are nodes
	the maximum number of authors to add to new graph

	and makes a graph with the query term as a node linked to all other nodes (the authors in the results)
	"""

	# Filter down results to max_authors, by picking the ones with longest lists of papers
	if len(results) > max_authors:
		top_authors = sorted(results.keys(), key=lambda k: len(results[k]), reverse=True)[:max_authors]
		
		filtered_results = {}
		for author in top_authors:
			filtered_results[author] = results[author]
		
		results = filtered_results

	# Make new graph and add query term as a node
	term_graph = nx.Graph()
	term_graph.add_node(query, {"name":query, "isTerm":True})

	# Add each author as a node and add an edge between the author and the query term
	for author, papers in results.items():
		name, authorid = author
		# Add relevant node and edge attributes
		term_graph.add_node(authorid, {"name": name, "paper_count": 1, "school":full_graph.node[authorid]["school"]})
		term_graph.add_edge(query, authorid, {
											"num_collabs": len(papers),
											"collab_title_url_years": papers
											})

	return term_graph






