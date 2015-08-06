import networkx as nx
from networkx.readwrite import json_graph
import json
import tfidf
import rake
import time

class GraphMaker(object):

	def __init__(self, dd, sn=None):
		self.data_dict = dd
		self.schl_names = sn
		self.graph = nx.Graph()
		self.populate_graph()


	def populate_graph(self):
		for title, info in self.data_dict.items():
			# Check if authors is a list of tuples (data from scraping) or of strings (data from oai)
			# Or use subclasses with different implementations of add_vertices here
			print "title is " + title.encode("utf-8")
			authors = info["authors"]
			if not authors:
				continue
			
			for author in authors:
				self.add_vertex(author)
			
			paper_url = info['url']
			self.add_links(title, paper_url, authors)

	# TODO consider using polymorphism here... having separate classes for data from scraper vs from oai
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
			#print "vertex id is ", vertex_id
			name = author[0]

		# TODO think graph.node can be replaced by just self.graph (also a dict)
		if vertex_id in self.graph.node:
			self.graph.node[vertex_id]["paper_count"] += 1
			# TODO now treating keywords as a string rather than list (concatenate rather than extend)
			#self.graph.node[vertex_id]["keywords"] += " " + keywords
		else:
			#self.graph.add_node(vertex_id, {"name": name, "paper_count": 1, "keywords": keywords})
			# TODO keywords do not go in this graph anymore
			self.graph.add_node(vertex_id, {"name": name, "paper_count": 1})
			in_school = self.check_schl_status(vertex_id)
			#print name, in_school
			# G.node returns {node: {attributes}} dictionary, can use this to set new attributes after node is created
			self.graph.node[vertex_id]["in_school"] = in_school


	def add_links(self, title, url, authors):
		# Check if authors is a list of collections or just strings
		# If collections, make new list out of element at index 1, which is the unique author url and the node id
		if not isinstance(authors[0], basestring):
			authors = [author[1] for author in authors]

		for i in range(0, len(authors)):
			for j in range(i+1, len(authors)):
				author1 = authors[i]
				author2 = authors[j]
				# Check if edge already exists, update edge attributes
				if self.graph.has_edge(author1, author2):
					self.graph[author1][author2]["num_collabs"] += 1
					self.graph[author1][author2]["collab_title_urls"].append([title, url])
				# If edge is new, add it to the graph, give it initial attributes
				else:
					self.graph.add_edge(author1, author2, {'num_collabs': 1, "collab_title_urls": [[title, url],]})


	def check_schl_status(self, author_id):
		
		if self.schl_names:
			# do name abbreviation here to ensure we get everyone?
			# TODO and lowercase to ensure consistency
			# TODO nb now using url to check school membership, more accurate
			for name_url in self.schl_names:
				if author_id in name_url:
					return True 
			
			return False 

		# If no list of names of school members has been provided (e.g. when data comes from OAI) return false
		# TODO or do something else??
		else:
			return False

	
	def get_graph(self):
		return self.graph

	# TODO change this path later
	def write_to_file(self, filename):
		graph_data = json_graph.node_link_data(self.graph)
		with open("../d3/" + filename + ".json", 'w') as f:
			json.dump(graph_data, f)
