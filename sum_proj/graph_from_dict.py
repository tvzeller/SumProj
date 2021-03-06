import networkx as nx
from networkx.readwrite import json_graph
import json
import tfidf
import rake
import time
import community
import operator
import textutils3 as tu

class CollabGraphMaker(object):

	def __init__(self, g=None):
		#self.data_dict = dd
		#self.schl_name_urls = []
		if g==None:
			self.graph = nx.Graph()
		else:
			self.graph = g
		#self.populate_graph()


	def populate_graph(self, data_dict, sn=None):
		self.schl_name_urls = sn

		for paper_id, info in data_dict.items():
			# Check if authors is a list of tuples (data from scraping) or of strings (data from oai)
			# Or use subclasses with different implementations of add_vertices here
			title = info["title"]
			#print "title is " + title.encode("utf-8")
			authors = info["authors"]
			if not authors:
				continue
			
			for author in authors:
				self.add_vertex(author)
			
			paper_url = info['url']
			paper_year = info['year']
			self.add_links(title, paper_url, paper_year, authors)

	def add_vertex(self, author):
		# author is either a (name, unique_url) pair or just a name string
		# If just a string, the name is used as both the node identifier and the "name" attribute
		# Otherwise access the (name, url) collection to get the url (to use as id) and the author name
		if isinstance(author, basestring):
			print "author is just a string!"
			vertex_id = author
			name = author
		else:
			vertex_id = author[1]
			name = author[0]

		# TODO think graph.node can be replaced by just self.graph (also a dict)
		if vertex_id in self.graph.node:
			self.graph.node[vertex_id]["paper_count"] += 1
		else:
			self.graph.add_node(vertex_id, {"name": name, "paper_count": 1})
			in_school = self.check_schl_status(vertex_id)
			# G.node returns {node: {attributes}} dictionary, can use this to set new attributes after node is created
			self.graph.node[vertex_id]["in_school"] = in_school


	def add_links(self, title, url, year, authors):
		# Check if authors is a list of collections or just strings
		# If collections, make new list out of element at index 1, which is the unique author url and the node id
		if not isinstance(authors[0], basestring):
			authors = [author[1] for author in authors]

		num_authors = len(authors)
		for i in range(0, num_authors):
			for j in range(i+1, num_authors):
				author1 = authors[i]
				author2 = authors[j]
				# Check if edge already exists, update edge attributes
				if self.graph.has_edge(author1, author2):
					self.graph[author1][author2]["weight"] += 1.0 / num_authors
					self.graph[author1][author2]["num_collabs"] += 1
					self.graph[author1][author2]["collab_title_url_years"].append([title, url, year])
				# If edge is new, add it to the graph, give it initial attributes
				else:
					self.graph.add_edge(author1, author2, {'weight': 1.0 / num_authors, "num_collabs": 1, "collab_title_url_years": [[title, url, year],]})


	def check_schl_status(self, author_id):
		
		if self.schl_name_urls:
			for name_url in self.schl_name_urls:
				if author_id in name_url:
					return True 
			
			return False 

		# If no list of names of school members has been provided (e.g. when data comes from OAI) return false
		else:
			return False


	def get_graph(self):
		return self.graph


####End of class#####


def write_to_file(g, path):
	graph_data = json_graph.node_link_data(g)
	with open(path, 'w') as f:
		json.dump(graph_data, f)


def add_metrics(g):
	deg_cent = nx.degree_centrality(g)
	close_cent = nx.closeness_centrality(g)
	between_cent = nx.betweenness_centrality(g)
	com = community.best_partition(g)

	sorted_coms = get_sorted_multimember_coms(com)

	for vertex in self.graph.node.keys():
		g.node[vertex]["deg_cent"] = deg_cent[vertex]
		g.node[vertex]["close_cent"] = close_cent[vertex]
		g.node[vertex]["between_cent"] = between_cent[vertex]
		if com[vertex] in sorted_coms:
			new_com_num = sorted_coms.index(com[vertex])

			g.node[vertex]["com"] = new_com_num + 1
		else:
			g.node[vertex]["com"] = False

	return g

def add_just_school_community(g):
	school_nodes = [node for node in g.node if g.node[node].get("in_school")]
	just_school_graph = g.subgraph(school_nodes)
	com = community.best_partition(just_school_graph)

	sorted_coms = get_sorted_multimember_coms(com)

	for vertex in just_school_graph.node.keys():
		if com[vertex] in sorted_coms:
			new_com_num = sorted_coms.index(com[vertex])
			g.node[vertex]["school_com"] = new_com_num + 1
		else:
			g.node[vertex]["school_com"] = False

	return g


def get_sorted_multimember_coms(com_dict):
	multimember_coms = set()
	for comnum in com_dict.values():
		if com_dict.values().count(comnum) > 1:
			multimember_coms.add(comnum)

	sorted_coms = sorted(multimember_coms)

	return sorted_coms

def add_com_keywords(akw, g):
	com_keywords = {}
	school_com_keywords = {}
	for author in akw:
		keywords = akw[author]["keywords"]
		keywords = [kw[0] for kw in keywords]
		com_num = g.node[author]["com"]
		# Use get as author may not have school_com
		school_com_num = g.node[author].get("school_com")
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
	g.graph[attr_name] = []
	for com, keywords in comkwdict.items():
		top_com_words = tu.get_most_frequent(keywords, 20)
		print "appending " + attr_name
		print top_com_words
		
		if attr_name in self.graph.graph: 
			g.graph[attr_name].append([com, top_com_words])
		else:
			g.graph[attr_name] = [[com, top_com_words],]

	return g

def make_sim_graph(akw, collab_graph_path):

	with open(collab_graph_path) as f:
		gdata = json.load(f)

	col_graph = json_graph.node_link_graph(gdata)

	sim_graph = nx.Graph()

	authors = akw.keys()
	values = akw.values()

	for i in range (0, len(authors)):
		author1 = authors[i]
		keywords = values[i]["keywords"]
		add_sim_graph_node(author1, keywords, sim_graph, col_graph)
		
		stemmed1 = set(tu.stem_word_list(keywords[:]))

		for j in range(i+1, len(authors)):
			author2 = authors[j]
			keywords2 = values[j]["keywords"]
			add_sim_graph_node(author2, keywords2, sim_graph, col_graph)
		
			stemmed2 = set(tu.stem_word_list(keywords2[:]))

			sim = tu.check_sim(stemmed1, stemmed2)
			ratio = sim[0]
			indices = sim[1]
			matched_words = []

			if len(keywords) > len(keywords2):
				longest = keywords
			else:
				longest = keywords2

			for index in indices:
				matched_words.append(longest[index])

			if ratio > 0.2:
				sim_graph.add_edge(author1, author2, {"num_collabs":ratio, "sim_kw": matched_words})
				if col_graph.has_edge(author1, author2):
					sim_graph[author1][author2]["areCoauthors"] = True

	return sim_graph

def add_sim_graph_node(node_id, keywords, sim_graph, col_graph):
	sim_graph.add_node(author1, {
									"name": col_graph.node[author1]["name"], 
									"in_school":col_graph.node[author1]["in_school"],
									"paper_count":col_graph.node[author1]["paper_count"],
									"keywords":keywords
									})




