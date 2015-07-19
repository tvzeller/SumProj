import networkx as nx

class GraphMaker(object):

	def __init__(self, dd, sn=None):
		self.data_dict = dd
		self.schl_names = sn
		self.graph = nx.Graph()
		self.populate_graph()


	def populate_graph(self):
		for title, authors in self.data_dict.items():
			self.add_vertices(authors)
			self.add_links(authors)


	def add_vertices(self, authors):		
		for author in authors:
			self.graph.add_node(author)	
			in_school = self.check_schl_status(author)
			# G.node returns {node: {attributes}} dictionary, can use this to set new attributes after node is created
			self.graph.node[author]["in_school"] = in_school


	def add_links(self, authors):
		for i in range(0, len(authors)):
			for j in range(i+1, len(authors)):
				self.graph.add_edge(authors[i], authors[j])


	def check_schl_status(self, name):
		if self.schl_names:
			# do name abbreviation here to ensure we get everyone?
			return name in self.schl_names
		# If no list of names of school members has been provided (e.g. when data comes from OAI) return false
		# TODO or do something else??
		else:
			return False

	def get_graph(self):

		return self.graph
