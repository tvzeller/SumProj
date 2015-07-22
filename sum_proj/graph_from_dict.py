import networkx as nx
from networkx.readwrite import json_graph
import json

class GraphMaker(object):

	def __init__(self, dd, sn=None):
		self.data_dict = dd
		self.schl_names = sn
		self.graph = nx.Graph()
		self.harmonise_names()
		self.populate_graph()


	def harmonise_names(self):
		if self.schl_names:
			self.schl_names = [(name.split(", ")[1] + " " + name.split(", ")[0]).lower() for name in self.schl_names]
		
		for title, authors in self.data_dict.items():
			authors = [author.split(", ")[1] + " " + author.split(", ")[0] for author in authors]
			self.data_dict[title] = authors

	def populate_graph(self):
		for title, authors in self.data_dict.items():
			self.add_vertices(authors)
			self.add_links(title, authors)


	def add_vertices(self, authors):		
		for author in authors:
			if author in self.graph.node:
				self.graph.node[author]["paper_count"] += 1
			else:
				self.graph.add_node(author)	
				in_school = self.check_schl_status(author)
				# G.node returns {node: {attributes}} dictionary, can use this to set new attributes after node is created
				self.graph.node[author]["in_school"] = in_school
				self.graph.node[author]["paper_count"] = 1


	def add_links(self, title, authors):
		for i in range(0, len(authors)):
			for j in range(i+1, len(authors)):
				if self.graph.has_edge(authors[i], authors[j]):
					self.graph[authors[i]][authors[j]]["num_collabs"] += 1
					self.graph[authors[i]][authors[j]]["collab_titles"].append(title)
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


