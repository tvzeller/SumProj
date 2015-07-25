import networkx as nx
from networkx.readwrite import json_graph
import json

class GraphMaker(object):

	def __init__(self, dd, sn=None):
		self.data_dict = dd
		self.schl_names = sn
		self.graph = nx.Graph()
		#self.harmonise_names()
		self.populate_graph()


	# Do this step before passing the data to here - this module should not have to handle this
	# def harmonise_names(self):
	# 	if self.schl_names:
	# 		self.schl_names = [(name.split(", ")[1] + " " + name.split(", ")[0]).lower() for name in self.schl_names]
		
	# 	for title, authors in self.data_dict.items():
	# 		authors = [author.split(", ")[1] + " " + author.split(", ")[0] for author in authors]
	# 		self.data_dict[title] = authors

	def populate_graph(self):
		for title, authors in self.data_dict.items():
			# Check if authors is a list of tuples (data from scraping) or of strings (data from oai)
			# Or use subclasses with different implementations of add_vertices here
			if not authors:
				continue

			if isinstance(authors[0], basestring):
				self.add_vertices(authors)
			else:
				self.add_vertices_from_tups(authors)
			self.add_vertices(authors)
			self.add_links(title, authors)


	def add_vertices(self, authors):		
		# When the data_dict value is a list of names
		for author_name in authors:
			self.add_vertex(author_name)
	
	def add_vertices_from_tups(self, authors):
		# When the data_dict value is a list of tuples
		for author_name, author_id in authors:
			self.add_vertex(author_id, author_name)


	def add_vertex(self, vertex_id, name=None):
		# In scraped data authors have a unique id number we can use in the graph structure
		# In oai data we just use the name as unique id and assume same name equals same person
		# In both cases the node is given a "name" attribute, to be used within the visualisation
		if name == None:
			name = vertex_id
		# TODO think graph.node can be replaced by just self.graph (also a dict)
		if vertex_id in self.graph.node:
			self.graph.node[vertex_id]["paper_count"] += 1
		else:
			self.graph.add_node(vertex_id, {"name": name, "paper_count": 1})
			in_school = self.check_schl_status(name)
			# G.node returns {node: {attributes}} dictionary, can use this to set new attributes after node is created
			self.graph.node[vertex_id]["in_school"] = in_school

	def add_links(self, title, authors):
		for i in range(0, len(authors)):
			for j in range(i+1, len(authors)):
				# Check if edge already exists, update edge attributes
				if self.graph.has_edge(authors[i], authors[j]):
					self.graph[authors[i]][authors[j]]["num_collabs"] += 1
					self.graph[authors[i]][authors[j]]["collab_titles"].append(title)
				# If edge is new, add it to the graph, give it initial attributes
				else:
					self.graph.add_edge(authors[i], authors[j], {'num_collabs': 1, "collab_titles": [title,]})


	def check_schl_status(self, name):
		if self.schl_names:
			# do name abbreviation here to ensure we get everyone?
			# TODO and lowercase to ensure consistency
			return name.lower() in self.schl_names
		# If no list of names of school members has been provided (e.g. when data comes from OAI) return false
		# TODO or do something else??
		else:
			return False

	
	def get_graph(self):
		return self.graph


	def write_to_file(self, filename):
		graph_data = json_graph.node_link_data(self.graph)
		with open("../d3/" + filename + ".json", 'w') as f:
			json.dump(graph_data, f)








